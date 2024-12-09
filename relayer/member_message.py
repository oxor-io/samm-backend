import re
import quopri
from email.message import Message
from email.parser import BytesParser
from email.utils import parseaddr

import dkim

import conf
import crud
from mailer.dkim_extractor import extract_dkim_data
from mailer.sender import send_email
from models import ApprovalData
from models import InitialData
from models import Member
from models import MemberMessage
from models import ProofStruct
from models import Transaction
from models import TransactionOperation
from models import TxData
from utils import convert_str_to_int_list
from utils import generate_merkle_tree
from utils import get_padded_email
from utils import generate_sequences


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

    if relayer_email != conf.RELAYER_EMAIL:
        print(f'Email To does not belong to Relayer {relayer_email} != {conf.RELAYER_EMAIL}')
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


async def send_response(msg: MemberMessage):
    await send_email(
        msg.member.email,
        subject='Relayer response',
        msg_text='Thank you for your message!',
    )
