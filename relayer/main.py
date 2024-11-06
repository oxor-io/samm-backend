#!/usr/bin/env python3
import asyncio
import os
import re
import quopri
from email.message import Message
from email.parser import BytesParser
from email.utils import parseaddr
from itertools import batched
import json

import dkim
from aioimaplib import aioimaplib
from dotenv import load_dotenv

RELAYER_SECRETS_FILE = os.environ.get('RELAYER_SECRETS_FILE')
load_dotenv(RELAYER_SECRETS_FILE or '.env')

import blockchain
import db
import crud
from mailer.dkim_extractor import extract_dkim_data
from mailer.sender import send_email
from models import ApprovalData
from models import InitialData
from models import Member
from models import MemberMessage
from models import MailboxCursor
from models import ProofStruct
from models import Transaction
from models import TransactionOperation
from models import TransactionStatus
from models import TxData
from utils import convert_str_to_int_list
from utils import generate_merkle_tree
from utils import get_padded_email
from utils import generate_sequences


# https://github.com/bamthomas/aioimaplib

IMAP_HOST = os.environ.get('IMAP_HOST')
RELAYER_EMAIL = os.environ.get('RELAYER_EMAIL')
IMAP_PORT = os.environ.get('IMAP_PORT')
RELAYER_TOKEN = os.environ.get('RELAYER_TOKEN')

# ID_HEADER_SET = 'Cc Content-Type In-Reply-To To Message-ID From Date References Subject Bcc DKIM-Signature'
# ID_HEADER_SET = 'From Date Subject DKIM-Signature'

FETCH_COMMAND = 'fetch'
# FETCH_CRITERIA_PARTS = 'FLAGS'
# FETCH_CRITERIA_PARTS = f'(UID FLAGS BODY.PEEK[HEADER.FIELDS ({ID_HEADER_SET})])'
FETCH_CRITERIA_PARTS = '(RFC822)'

FETCH_MESSAGE_DATA_SEQNUM = re.compile(rb'(?P<seqnum>\d+) FETCH.*')
FETCH_MESSAGE_DATA_UID = re.compile(rb'.*UID (?P<uid>\d+).*')
FETCH_MESSAGE_DATA_FLAGS = re.compile(rb'.*FLAGS \((?P<flags>.*?)\).*')

CHUNK_SIZE = 100

CURSORS = [
    MailboxCursor(folder='Spam', uid_start=95, uid_end=95 + CHUNK_SIZE),
    MailboxCursor(folder='INBOX', uid_start=250, uid_end=250 + CHUNK_SIZE),
]


async def idle_loop(host, port, user):
    imap_client = aioimaplib.IMAP4_SSL(host=host, port=port)
    resp = await imap_client.wait_hello_from_server()
    print(f'Hello server: {resp}')

    resp = await imap_client.xoauth2(user, RELAYER_TOKEN)
    print(f'Auth: {resp}')

    # resp = await imap_client.list('INBOX\\', '*')
    # print(f'List mail folder: {resp}')

    cursor = CURSORS[0]
    switch_folder = True

    while True:
        if switch_folder:
            idx = CURSORS.index(cursor)
            cursor = CURSORS[0] if (idx + 1) >= len(CURSORS) else CURSORS[idx + 1]
            resp = await imap_client.select(cursor.folder)
            switch_folder = False
            print(f'Select mail folder: folder={cursor.folder} resp={resp}')

        uid_max = await fetch_imap_messages(imap_client, cursor.uid_start, cursor.uid_end)
        match uid_max:
            case 0:
                switch_folder = True
            case cursor.uid_end:
                cursor.uid_start += CHUNK_SIZE
                cursor.uid_end += CHUNK_SIZE
                switch_folder = True
            case _:
                cursor.uid_start = uid_max + 1
                cursor.uid_end = uid_max + CHUNK_SIZE


async def fetch_imap_messages(imap_client, uid_start: int, uid_end: int) -> int:
    resp = await imap_client.uid(FETCH_COMMAND, f'{uid_start}:{uid_end}', FETCH_CRITERIA_PARTS)
    print(f'Fetch mails UIDs={uid_start}:{uid_end} (lines={len(resp.lines)} / 3)')

    if resp.result != 'OK':
        print(f'Fetch command return an error: {resp}')
        raise

    uid_max = await process_imap_messages(resp.lines)
    print(f'Fetched uid_max={uid_max}')

    idle = await imap_client.idle_start(timeout=20)
    print(f'IDLE resp: {idle}')

    resp = await imap_client.wait_server_push()
    print(f'QUEUE resp: {resp}')

    imap_client.idle_done()

    await asyncio.wait_for(idle, 30)

    return uid_max


async def process_imap_messages(lines: list) -> int:
    uid_max = 0

    for start, raw_msg, end in batched(lines[:-1], 3):
        fetch_command_without_literal = b'%s %s' % (start, end)
        uid: int = int(FETCH_MESSAGE_DATA_UID.match(fetch_command_without_literal).group('uid'))
        # flags=FETCH_MESSAGE_DATA_FLAGS.match(fetch_command_without_literal).group('flags'),
        # sequence_number: int = FETCH_MESSAGE_DATA_SEQNUM.match(fetch_command_without_literal).group('seqnum')

        # # Just print from/to/subject of received emails
        # msg: Message = BytesParser().parsebytes(raw_msg)
        # _, member_email = parseaddr(msg['From'])
        # _, relayer_email = parseaddr(msg['To'])
        # msg_hash = msg['Subject']
        # print(f'Raw message is parsed: uid={uid} from={member_email} to={relayer_email} subj={msg_hash}')
        # if uid > uid_max:
        #     uid_max = uid
        # continue

        print(f'Parse raw message: UID={uid}')
        member_message = await parse_member_message(uid, raw_msg)

        # TODO: refactoring for batch operations - create zk_proofs, save to DB and email
        if member_message:
            proof_struct = await generate_zk_proof(member_message.approval_data)
            member_message.tx = await store_member_message(uid, member_message, proof_struct)

            is_confirmed, proof_structs = await check_threshold(member_message.tx)
            if is_confirmed:
                tx_status = await execute_transaction(member_message.tx, proof_structs)
                await change_transaction_status(member_message.tx, tx_status)

            # TODO: notice all members if the new tx is received
            await send_response(member_message)

        if uid > uid_max:
            uid_max = uid

    return uid_max


async def parse_member_message(uid: int, raw_msg: bytes) -> MemberMessage | None:
    # verify DKIM
    print('Verify DKIM')
    if not await dkim.verify_async(raw_msg):
        print('DKIM is not valid')
        return None

    # parse email message
    print('Parse raw message')
    msg: Message = BytesParser().parsebytes(raw_msg)
    _, member_email = parseaddr(msg['From'])
    _, relayer_email = parseaddr(msg['To'])
    msg_hash = msg['Subject']
    print(f'Raw message is parsed: from={member_email} to={relayer_email} subj={msg_hash}')

    if relayer_email != RELAYER_EMAIL:
        print(f'Email To does not belong to Relayer {relayer_email} != {RELAYER_EMAIL}')
        return None

    print('Check msg_hash')
    # # TODO: check msgHash format
    # pattern = re.compile(r'\b[0-9a-fA-F]{64}\b')
    # match = re.match(pattern, 'hash')
    # print(match.group(0))  # hash
    if not msg_hash:
        print(f'msgHash format is not correct: {msg_hash}')
        return None

    # TODO: what the samm_id is used?
    print('Check member FROM email')
    member = await crud.get_member_by_email(member_email)
    if not member:
        print(f'Email From is not a member: {member_email}')
        return None

    # TODO: optimize via IMAP server flags
    print('Check already processed message UID')
    if await crud.get_approval_by_uid(email_uid=uid):
        print(f'The email UID already was registered: {uid}')
        # TODO: mb raise
        return None

    initial_data: InitialData | None = None
    tx = await crud.get_tx_by_msg_hash(msg_hash)
    if not tx:
        print('Transaction initialization')

        body = parse_body(msg)
        samm_id, tx_data = extract_tx_data(body)
        if not samm_id or not tx_data:
            print(f'Wrong initial data: body={body}')
            return None
        members = await crud.get_members_by_samm(samm_id)
        initial_data = InitialData(
            samm_id=samm_id,
            msg_hash=msg_hash,
            tx_data=tx_data,
            members=members,
        )
    else:
        print('Transaction approval')

        # TODO: check tx_status or deadline if approval
        if await crud.get_approval_by_tx_and_email(tx_id=tx.id, member_id=member.id):
            print(f'Dublicate approval: tx={tx.id} member={member.id}')
            return None
        members = await crud.get_members_by_tx(tx.id)

    print('Assemble approval data')
    approval_data = await create_approval_data(raw_msg, msg_hash, members, member, relayer_email)
    return MemberMessage(
        member=member,
        tx=tx,
        initial_data=initial_data,
        approval_data=approval_data,
    )


def parse_body(msg: Message) -> str:
    if not msg.is_multipart():
        # not multipart - i.e. plain text, no attachments, keeping fingers crossed
        return msg.get_payload()

    for part in msg.walk():
        c_type = part.get_content_type()
        c_disposition = str(part.get('Content-Disposition'))
        c_transfer_encoding = str(part.get('Content-Transfer-Encoding'))

        # skip any text/plain (txt) attachments
        if c_type == 'text/plain' and 'attachment' not in c_disposition:
            if c_transfer_encoding == 'quoted-printable':
                return quopri.decodestring(part.get_payload().encode()).decode()
            return part.get_payload()

    return ''


def extract_tx_data(body: str) -> tuple[int, TxData] | tuple[None, None]:
    # TODO: extraction format
    # TODO: newline character is not taken into account!
    m = re.match(r'samm_id=(?P<samm_id>.*);'
                 r'to=(?P<to>.*);'
                 r'value=(?P<value>.*);'
                 r'data=(?P<data>.*);'
                 r'operation=(?P<operation>.*);'
                 r'nonce=(?P<nonce>.*);'
                 r'deadline=(?P<deadline>.*);', body)
    try:
        return (
            int(m.group('samm_id')),
            TxData(
                to=str(m.group('to')),
                value=int(m.group('value')),
                data=bytes(m.group('data').encode()),
                operation=TransactionOperation(m.group('operation')),
                nonce=int(m.group('nonce')),
                deadline=int(m.group('deadline')),
            )
        )
    except (AttributeError, ValueError) as e:  # no match or failed conversion
        print('Tx data extraction is failed: ', e)
        return None, None

    # TODO: check tx_data fields


async def create_approval_data(raw_msg: bytes, msg_hash_b64: str, members: list[Member], member: Member, relayer_email: str):
    domain, header, header_length, key_size, pubkey_modulus_limbs, redc_params_limbs, signature_limbs = \
        await extract_dkim_data(raw_msg)
    msg_hash = convert_str_to_int_list(msg_hash_b64)
    padded_member, padded_member_length = get_padded_email(member.email)
    padded_relayer, padded_relayer_length = get_padded_email(relayer_email)

    emails_and_secrets = [(member.email, member.secret) for member in members]
    tree = generate_merkle_tree(emails_and_secrets)
    path_elements, path_indices = tree.gen_proof(leaf_pos=members.index(member))

    # calculate sequences
    from_seq, member_seq, to_seq, relayer_seq = generate_sequences(header, header_length, member.email, relayer_email)

    return ApprovalData(
        domain=domain,
        header=header,
        header_length=header_length,

        msg_hash=msg_hash,

        padded_member=padded_member,
        padded_member_length=padded_member_length,
        secret = member.secret,
        padded_relayer=padded_relayer,
        padded_relayer_length=padded_relayer_length,

        key_size=key_size,
        pubkey_modulus_limbs=pubkey_modulus_limbs,
        redc_params_limbs=redc_params_limbs,
        signature=signature_limbs,

        root=str(tree.root),
        path_elements=[str(i) for i in path_elements],
        path_indices=path_indices,

        from_seq=from_seq,
        member_seq=member_seq,
        to_seq=to_seq,
        relayer_seq=relayer_seq,
    )


async def generate_zk_proof(approval_data: ApprovalData) -> ProofStruct:

    proverData = {
        "root": approval_data.root,
        "path_elements" : approval_data.path_elements,
        "path_indices" : approval_data.path_indices,
        "signature" : approval_data.signature,
        "padded_member" : approval_data.padded_member,
        "secret" : approval_data.secret,
        "msg_hash" : approval_data.msg_hash,
        "header" : { "len" : approval_data.header_length, "storage" : approval_data.header },
        "relayer" : { "len" : approval_data.padded_relayer_length, "storage" : approval_data.padded_relayer },
        "pubkey" : { "modulus" : approval_data.pubkey_modulus_limbs, "redc" : approval_data.redc_params_limbs },
        "from_seq" : { "index" : approval_data.from_seq.index, "length" : approval_data.from_seq.length },
        "member_seq" : { "index" : approval_data.member_seq.index, "length" : approval_data.member_seq.length },
        "to_seq" : { "index" : approval_data.to_seq.index, "length" : approval_data.to_seq.length },
        "relayer_seq" : { "index" : approval_data.relayer_seq.index, "length" : approval_data.relayer_seq.length }
    }
    
    # Serializing json
    json_object = json.dumps(proverData, indent=4)

    # write to prover file
    with open('./target/prover.json', 'w') as file:  
        file.write(json_object)

    # node scripts/generateWitness.js
    print('Generating witness... ⌛')
    process = await asyncio.create_subprocess_exec('node', 'scripts/generateWitness.js')
    print(f'subprocess: {process}')
    await process.wait()
    print('Generating witness... ✅')

    print('Generating proof... ⌛')
    # bb prove_ultra_keccak_honk -b ./target/samm_2048.json -w ./target/witness.gz -o ./target/proof
    process = await asyncio.create_subprocess_exec('bb', 'prove_ultra_keccak_honk', '-b', './target/samm_2048.json', '-w', './target/witness.gz', '-o', './target/proof')
    print(f'subprocess: {process}')
    await process.wait()
    print('Generating proof... ✅')

    # read proof and split to public inputs, outputs (commit, pubkeyHash) and proof itself
    data = b''
    with open('./target/proof', 'rb') as file:
        data = file.read()
    
    # first output
    commit = data[5540:5572].hex()
    # second output
    pubkeyHash = data[5572:5604].hex()
    # proof
    proof = data[4:100].hex() + data[5604:].hex()

    match approval_data.key_size:
        case 2048:
            is_2048_sig = True
        case 1024:
            is_2048_sig = False
        case _:
            # TODO: error
            raise

    return ProofStruct(
        proof=proof,
        commit=commit,
        domain=approval_data.domain,
        pubkeyHash=pubkeyHash,
        is2048sig=is_2048_sig,
    )



async def store_member_message(uid: int, msg: MemberMessage, proof_struct: ProofStruct) -> Transaction:
    tx = msg.tx
    if msg.initial_data and tx or not msg.initial_data and not tx:
        raise

    if msg.initial_data:
        tx = await crud.create_tx(msg.initial_data)

    await crud.create_approval(tx, msg.member, proof_struct, uid)
    print(f'UID={uid}')
    print(f'FROM={msg.member.email}')
    print(f'TX={tx.id}')
    print(f'ZKPROOF={proof_struct}')
    return tx


async def check_threshold(tx: Transaction) -> tuple[bool, list[ProofStruct]]:
    if not await crud.check_threshold_is_confirmed(tx.id, tx.samm_id):
        return False, []

    proof_structs: list[ProofStruct] = []
    for approval in await crud.get_approvals(tx.id):
        proof_structs.append(ProofStruct(
            proof=approval.proof,
            commit=approval.commit.from_bytes(32),
            domain=approval.domain,
            pubkeyHash=approval.pubkey_hash,
            is2048sig=approval.is_2048_sig,
        ))

    if not proof_structs:
        print('Proofs list is empty')
        raise

    return True, proof_structs


async def execute_transaction(tx: Transaction, proof_structs: list[ProofStruct]) -> TransactionStatus:
    tx_data = TxData(
        to=tx.to,
        value=tx.value,
        data=tx.data,
        operation=TransactionOperation(tx.operation),
        nonce=tx.nonce,
        deadline=tx.deadline,
    )
    is_sent = await blockchain.execute_transaction(tx.samm.samm_address, tx_data, proof_structs)
    return TransactionStatus.sent if is_sent else TransactionStatus.confirmed


async def change_transaction_status(tx: Transaction, status: TransactionStatus):
    # match status:
    #     case TransactionStatus.pending:
    #         # do nothing
    #         pass
    #     case TransactionStatus.success:
    #         # TODO: change tx.status to success
    #         pass
    #     case TransactionStatus.confirmed | TransactionStatus.sent | TransactionStatus.failed:
    #         # TODO: sent - strange state of tx
    #         # TODO: change tx.status
    #         print('tx')
    #     case _:
    #         print('Incorrect status')
    #         # TODO: return?
    await crud.change_transaction_status(tx.tx_id, status)


async def send_response(msg: MemberMessage):
    await send_email(
        msg.member.email,
        subject='Relayer response',
        msg_text='Thank you for your message!',
    )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.init_db())
    # TODO: remove or refactor the fill_db_initial_tx function before release
    loop.run_until_complete(crud.fill_db_initial_tx(first_user_email='artem@oxor.io'))
    loop.run_until_complete(idle_loop(IMAP_HOST, IMAP_PORT, RELAYER_EMAIL))
