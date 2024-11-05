#!/usr/bin/env python3
import asyncio
import os
import re
from datetime import datetime
from email.message import Message
from email.parser import BytesParser
from email.utils import parseaddr
from itertools import batched
import json

import dkim
from aioimaplib import aioimaplib
from dotenv import load_dotenv
load_dotenv()

import db
import crud
from mailer.dkim_extractor import extract_dkim_data
from mailer.sender import send_email
from models import ApprovalData
from models import InitialData
from models import Member
from models import MessageAttributes
from models import MemberMessage
from models import TransactionOperation
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

CHUNK_SIZE = 10


async def idle_loop(host, port, user):
    imap_client = aioimaplib.IMAP4_SSL(host=host, port=port)
    resp = await imap_client.wait_hello_from_server()
    print(f'Hello server: {resp}')

    resp = await imap_client.xoauth2(user, RELAYER_TOKEN)
    print(f'Auth: {resp}')

    resp = await imap_client.select()
    print(f'Select mail folder: {resp}')

    uid_start = 1
    uid_end = CHUNK_SIZE
    while True:
        # TODO: pagination?
        uid_range = f'{uid_start}:{uid_end}'
        resp = await imap_client.uid(FETCH_COMMAND, uid_range, FETCH_CRITERIA_PARTS)
        print(f'Fetch mails UIDs={uid_range} (lines={len(resp.lines)} / 3)')

        if resp.result != 'OK':
            raise

        uid_max, messages_attrs = await process_imap_messages(resp.lines)
        print(f'Fetched uid_max={uid_max}')

        idle = await imap_client.idle_start(timeout=60)
        print(f'IDLE resp: {idle}')

        resp = await imap_client.wait_server_push()
        print(f'QUEUE resp: {resp}')

        imap_client.idle_done()

        if uid_max == uid_end:
            uid_start += CHUNK_SIZE
            uid_end += CHUNK_SIZE
        elif uid_max != 0:
            uid_start = uid_max + 1
            uid_end = uid_max + CHUNK_SIZE

        await asyncio.wait_for(idle, 30)


async def process_imap_messages(lines: list) -> tuple[int, list[MessageAttributes]]:
    uid_max = 0
    messages_attrs: list[MessageAttributes] = []

    for start, raw_msg, end in batched(lines[:-1], 3):
        fetch_command_without_literal = b'%s %s' % (start, end)
        uid: int = int(FETCH_MESSAGE_DATA_UID.match(fetch_command_without_literal).group('uid'))
        # flags=FETCH_MESSAGE_DATA_FLAGS.match(fetch_command_without_literal).group('flags'),
        sequence_number: int = FETCH_MESSAGE_DATA_SEQNUM.match(fetch_command_without_literal).group('seqnum')
        member_message = await parse_member_message(uid, raw_msg)

        # TODO: refactoring for batch operations - create zk_proofs, save to DB and email
        if member_message:
            zk_proof = await generate_zk_proof(member_message.approval_data)
            await store_member_message(uid, member_message, zk_proof)
            # TODO: notice all members if the new tx is received
            await send_response(member_message)

        messages_attrs.append(MessageAttributes(
            uid=uid,
            # flags=flags,
            sequence_number=sequence_number,
            member_message=member_message,
        ))

        if uid > uid_max:
            uid_max = uid

    return uid_max, messages_attrs


async def parse_member_message(uid: int, raw_msg: bytes) -> MemberMessage | None:
    # verify DKIM
    if not await dkim.verify_async(raw_msg):
        print('DKIM is not valid')
        return None

    # parse email message
    msg: Message = BytesParser().parsebytes(raw_msg)
    _, member_email = parseaddr(msg['From'])
    _, relayer_email = parseaddr(msg['To'])
    msg_hash = msg['Subject']

    if relayer_email != RELAYER_EMAIL:
        print(f'Email To does not belong to Relayer {relayer_email} != {RELAYER_EMAIL}')
        return None

    # TODO: check msgHash format
    if not msg_hash:
        print(f'msgHash format is not correct: {msg_hash}')
        return None

    # TODO: what the samm_id is used?
    member = await crud.get_member_by_email(member_email)
    if not member:
        print(f'Email From is not a member: {member_email}')
        return None

    # TODO: optimize via IMAP server flags
    if await crud.get_approval_by_uid(email_uid=uid):
        print(f'The email UID already was registered: {uid}')
        # TODO: mb raise
        return None

    initial_data: InitialData | None = None
    tx = await crud.get_tx_by_msg_hash(msg_hash)
    if not tx:
        # TX initialization
        body = parse_body(msg)
        samm_id, tx_data = extract_tx_data(body)
        if not samm_id or not tx_data:
            raise
        members = await crud.get_members_by_samm(samm_id)
        initial_data = InitialData(
            samm_id=samm_id,
            msg_hash=msg_hash,
            tx_data=tx_data,
            members=members,
        )
    else:
        # TX approval
        # TODO: check tx_status or deadline if approval
        if await crud.get_approval_by_tx_and_email(tx_id=tx.id, member_id=member.id):
            print(f'Dublicate approval: tx={tx.id} member={member.id}')
            return None
        members = await crud.get_members_by_tx(tx.id)

    approval_data = create_approval_data(raw_msg, msg_hash, members, member, relayer_email)
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

        # skip any text/plain (txt) attachments
        if c_type == 'text/plain' and 'attachment' not in c_disposition:
            return part.get_payload()

    return ''


def extract_tx_data(body: str) -> tuple[int, TxData] | tuple[None, None]:
    # TODO: extraction format
    m = re.match(r'samm_id=(?P<samm_id>.*); to=(?P<to>.*); value=(?P<value>.*); data=(?P<data>.*);'
                 r' operation=(?P<operation>.*); nonce=(?P<nonce>.*); deadline=(?P<deadline>.*);', body)
    try:
        return (
            int(m.group('samm_id')),
            TxData(
                to=str(m.group('to')),
                value=int(m.group('value')),
                data=str(m.group('data')),
                operation=TransactionOperation(m.group('operation')),
                nonce=int(m.group('nonce')),
                deadline=datetime.strptime(str(m.group('deadline')), '%Y-%m-%d %H:%M'),
            )
        )
    except (AttributeError, ValueError):  # no match or failed conversion
        return None, None


def create_approval_data(raw_msg: bytes, msg_hash_b64: str, members: list[Member], member: Member, relayer_email: str):
    header, header_length, pubkey_modulus_limbs, redc_params_limbs, signature_limbs = extract_dkim_data(raw_msg)
    msg_hash = convert_str_to_int_list(msg_hash_b64)
    padded_member, padded_member_length = get_padded_email(member.email)
    padded_relayer, padded_relayer_length = get_padded_email(relayer_email)

    emails_and_secrets = [(member.email, member.secret) for member in members]
    tree = generate_merkle_tree(emails_and_secrets)
    path_elements, path_indices = tree.gen_proof(leaf_pos=members.index(member))

    # calculate sequences
    from_seq, member_seq, to_seq, relayer_seq = generate_sequences(header, header_length, member.email, relayer_email)

    return ApprovalData(
        header=header,
        header_length=header_length,

        msg_hash=msg_hash,

        padded_member=padded_member,
        padded_member_length=padded_member_length,
        secret = member.secret,
        padded_relayer=padded_relayer,
        padded_relayer_length=padded_relayer_length,

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


async def generate_zk_proof(approval_data: ApprovalData) -> str:

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

    return 'TODO: zk proof'


async def store_member_message(uid: int, msg: MemberMessage, zk_proof: str):
    tx = msg.tx
    if msg.initial_data and tx or not msg.initial_data and not tx:
        raise

    if msg.initial_data:
        tx = await crud.create_tx(msg.initial_data)

    await crud.create_approval(tx, msg.member, zk_proof, uid)

    print(f'UID={uid}')
    print(f'FROM={msg.member.email}')
    print(f'TX={tx.id}')
    print(f'ZKPROOF={zk_proof}')


async def send_response(msg: MemberMessage):
    await send_email(
        msg.member.email,
        subject='Relayer response',
        msg_text='Thank you for your message!',
    )


if __name__ == '__main__':
    db.init_db()
    loop = asyncio.get_event_loop()
    # loop.run_until_complete(crud.fill_db())
    loop.run_until_complete(idle_loop(IMAP_HOST, IMAP_PORT, RELAYER_EMAIL))
