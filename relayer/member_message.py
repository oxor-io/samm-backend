import asyncio
import re
from email import policy
from email.message import Message
from email.parser import BytesParser
from email.utils import parseaddr

import dkim

import conf
import crud
from mailer.dkim_extractor import extract_dkim_data
from mailer.sender import send_email
from mailer.body_parser import parse_body
from models import ApprovalData
from models import InitialData
from models import Member
from models import MemberMessage
from models import ProofStruct
from models import Txn
from models import TxnOperation
from models import TxnData
from utils import convert_str_to_int_list
from utils import generate_merkle_tree
from utils import get_padded_email
from utils import generate_sequences
from prover import generate_zk_proof
from txn_execution import check_threshold
from txn_execution import execute_txn
from txn_execution import change_txn_status
from logger import logger


async def parse_member_message(uid: int, raw_msg: bytes) -> MemberMessage | None:
    # verify DKIM
    logger.info('Verify DKIM')
    if not await dkim.verify_async(raw_msg):
        logger.warning('DKIM is not valid')
        return None

    # parse email message
    logger.info('Parse raw message')
    msg: Message = BytesParser(policy=policy.default).parsebytes(raw_msg)
    _, member_email = parseaddr(msg['From'])
    _, relayer_email = parseaddr(msg['To'])
    msg_hash = msg['Subject']
    logger.info(f'Raw message is parsed: from={member_email} to={relayer_email} subj={msg_hash}')

    logger.info('Check relayer email')
    if relayer_email != conf.RELAYER_EMAIL:
        logger.warning(f'Email "To" does not belong to Relayer: {relayer_email} != {conf.RELAYER_EMAIL}')
        return None

    logger.info('Check msg_hash')
    # # TODO: check msgHash format
    # pattern = re.compile(r'\b[0-9a-fA-F]{64}\b')
    # match = re.match(pattern, 'hash')
    # print(match.group(0))  # hash
    if not msg_hash:
        logger.warning(f'msgHash format is not correct: {msg_hash}')
        return None

    logger.info('Check member by "From" email')
    member = await crud.get_member_by_email(member_email)
    if not member:
        logger.warning(f'Email "From" is not a member: {member_email}')
        return None

    # TODO: optimize via IMAP server flags
    logger.info('Check already processed message UID')
    if await crud.get_approval_by_uid(email_uid=uid):
        logger.error(f'The email UID already was registered: {uid}')
        return None

    txn = await crud.get_txn_by_msg_hash(msg_hash)
    if txn:
        logger.info('Transaction approval')
        members, initial_data = (await _process_approval_message(txn.id, member.id)),  None
    else:
        logger.info('Transaction initialization')
        members, initial_data = await _process_initial_message(msg, msg_hash)

    if not members:
        return None

    logger.info('Assemble approval data')
    approval_data = await create_approval_data(raw_msg, msg_hash, members, member, relayer_email)
    return MemberMessage(
        member=member,
        txn=txn,
        initial_data=initial_data,
        approval_data=approval_data,
    )


async def _process_initial_message(msg, msg_hash) -> tuple[list[Member], InitialData | None]:
    body = parse_body(msg)
    samm_id, txn_data = extract_txn_data(body)
    if not samm_id or not txn_data:
        logger.error(f'Wrong initial data: body={body}')
        return [], None

    members = await crud.get_members_by_samm(samm_id)
    if not members:
        logger.error(f'No members for samm_id: {samm_id}')
        return [], None

    initial_data = InitialData(
        samm_id=samm_id,
        msg_hash=msg_hash,
        txn_data=txn_data,
        members=members,
    )
    return members, initial_data


async def _process_approval_message(txn_id: int, member_id: int) -> list[Member]:
    # TODO: check txn_status or deadline if approval
    if await crud.get_approval_by_txn_and_email(txn_id=txn_id, member_id=member_id):
        logger.error(f'Dublicate approval: tx={txn_id} member={member_id}')
        return []

    members = await crud.get_members_by_txn(txn_id)
    return members


def extract_txn_data(body: str) -> tuple[int, TxnData] | tuple[None, None]:
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
            TxnData(
                to=str(m.group('to')),
                value=int(m.group('value')),
                data=bytes(m.group('data').encode()),
                operation=TxnOperation(m.group('operation')),
                nonce=int(m.group('nonce')),
                deadline=int(m.group('deadline')),
            )
        )
    except (AttributeError, ValueError):  # no match or failed conversion
        logger.exception('Tx data extraction is failed.')
        return None, None

    # TODO: validate txn_data fields


def calculate_samm_root(members: list[Member]):
    # TODO: less predictable order
    members.sort(key=lambda x: x.id)
    emails_and_secrets = [(member.email, member.secret) for member in members]
    tree = generate_merkle_tree(emails_and_secrets)
    return str(tree.root), tree


async def create_approval_data(raw_msg: bytes, msg_hash_b64: str, members: list[Member], member: Member, relayer_email: str):
    domain, header, header_length, key_size, pubkey_modulus_limbs, redc_params_limbs, signature_limbs = \
        await extract_dkim_data(raw_msg)
    msg_hash = convert_str_to_int_list(msg_hash_b64)
    padded_member, padded_member_length = get_padded_email(member.email)
    padded_relayer, padded_relayer_length = get_padded_email(relayer_email)

    root, tree = calculate_samm_root(members)
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
        secret=member.secret,
        padded_relayer=padded_relayer,
        padded_relayer_length=padded_relayer_length,

        key_size=key_size,
        pubkey_modulus_limbs=pubkey_modulus_limbs,
        redc_params_limbs=redc_params_limbs,
        signature=signature_limbs,

        root=root,
        path_elements=[str(i) for i in path_elements],
        path_indices=path_indices,

        from_seq=from_seq,
        member_seq=member_seq,
        to_seq=to_seq,
        relayer_seq=relayer_seq,
    )


async def process_member_message(uid: int, member_message) -> tuple[bool, Txn | None]:
    proof_struct = await generate_zk_proof(member_message.approval_data)
    if not proof_struct:
        # TODO: send response that we could not generate proof
        return False, None

    txn = await store_member_message(uid, member_message, proof_struct)

    is_confirmed, proof_structs = await check_threshold(txn)
    if is_confirmed:
        txn_status = await execute_txn(txn, proof_structs)
        txn = await change_txn_status(txn, txn_status)

    return is_confirmed, txn


async def store_member_message(uid: int, msg: MemberMessage, proof_struct: ProofStruct) -> Txn:
    # TODO: commit new txn and approval in the same session
    logger.info(f'Store member message info')

    txn = msg.txn
    if msg.initial_data and txn or not msg.initial_data and not txn:
        logger.error('Collision of initial data and txn')
        raise

    if msg.initial_data:
        await crud.create_txn(msg.initial_data)
        txn = await crud.get_txn_by_msg_hash(msg.initial_data.msg_hash)
        logger.info('New txn is stored')

    await crud.create_approval(txn, msg.member, proof_struct, uid)
    logger.info('New approval is stored')
    return txn


async def send_response_by_member_message(msg: MemberMessage, txn: Txn, is_confirmed: bool):
    if is_confirmed:
        members = await crud.get_members_by_txn(txn.id)
        await send_response_confirmation(txn.msg_hash, members)
    elif msg.initial_data:
        members = [m for m in msg.initial_data.members if m != msg.member]
        await send_response_initial(txn.msg_hash, members)
        await send_response_me(txn.msg_hash, msg.member)
    else:
        await send_response_me(txn.msg_hash, msg.member)


async def send_response_initial(msg_hash: str, members: list[Member]):
    for member in members:
        await send_email(
            member.email,
            subject='New transaction in SAMM',
            msg_text=f'A new transaction with hash {msg_hash} has been created in SAMM. '
                     f'Visit {conf.SAMM_APP_URL} to approve the transaction.',
        )
        await asyncio.sleep(5)


async def send_response_confirmation(msg_hash: str, members: list[Member]):
    for member in members:
        await send_email(
            member.email,
            subject='Confirmation threshold is reached in SAMM',
            msg_text=f'The transaction with hash {msg_hash} has been approved by SAMM participants. '
                     f'Visit {conf.SAMM_APP_URL} for more details.',
        )
        await asyncio.sleep(5)


async def send_response_me(msg_hash: str, current_member: Member):
    await send_email(
        current_member.email,
        subject='Relayer response',
        msg_text=f'Your confirmation of the transaction with hash {msg_hash} has been accepted. '
                 f'Thank you for your participation!',
    )
