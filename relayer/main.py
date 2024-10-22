#!/usr/bin/env python3
import asyncio
import os
import re
from dataclasses import dataclass
from email.message import Message
from email.parser import BytesParser
from email.utils import parseaddr
from itertools import batched

import dkim
from aioimaplib import aioimaplib
from dotenv import load_dotenv
load_dotenv()

import db
import crud
from sender import send_email


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


@dataclass
class TxData:
    to: int
    value: int
    data: str
    operation: str
    nonce: int


@dataclass
class MemberMessage:
    member_name: str
    member_email: str
    date: str
    dkim_signature: bytes
    msg_hash: str
    initial_tx: TxData | None


@dataclass
class MessageAttributes:
    uid: int
    # flags: list[str]
    sequence_number: int
    member_message: MemberMessage | None


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
            zk_proof = await create_zk_proof(member_message)
            await store_member_message(uid, member_message, zk_proof)
            # TODO: uncomment
            # await send_response(member_message)

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
    if not dkim.verify(raw_msg):
        return None

    # parse email message
    msg: Message = BytesParser().parsebytes(raw_msg)
    member_name, member_email = parseaddr(msg['From'])
    msg_hash = msg['Subject']

    # # TODO: check To?
    # if msg['To'] != RELAYER_EMAIL:
    #     raise

    # TODO: check msgHash format
    if not msg_hash:
        raise

    member = await crud.get_member_by_email(member_email)
    # TODO: uncomment
    # if not member:
    #     raise

    # TODO: optimize via IMAP server flags
    if await crud.get_approval_by_uid(email_uid=uid):
        raise

    initial_tx: TxData | None = None
    tx = await crud.get_tx_by_msg_hash(msg_hash)
    if not tx:
        # TX initialization
        body = parse_body(msg)
        initial_tx = extract_tx_data(body)
        # TODO: uncomment
        # if not initial_tx:
        #     raise
    else:
        # TX approval
        # TODO: check tx_status or deadline if approval
        if await crud.get_approval_by_tx_and_email(tx_id=tx.id, member_id=member.id):
            raise

    return MemberMessage(
        member_name=member_name,
        member_email=member_email,
        date=msg['Date'],
        dkim_signature=msg['DKIM-Signature'],
        msg_hash=msg_hash,
        initial_tx=initial_tx,
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


def extract_tx_data(body: str) -> TxData | None:
    # TODO: extraction format
    m = re.match(r'to=(?P<to>.*); value=(?P<value>.*); data=(?P<data>.*);'
                 r' operation=(?P<operation>.*); nonce=(?P<nonce>.*);', body)
    try:
        return TxData(
            to=int(m.group('to')),
            value=int(m.group('value')),
            data=str(m.group('data')),
            operation=str(m.group('operation')),
            nonce=int(m.group('nonce')),
        )
    except (AttributeError, ValueError):  # no match or failed conversion
        return


async def create_zk_proof(msg: MemberMessage) -> str:
    # TODO: launch prover
    return ''


async def store_member_message(uid, msg: MemberMessage, zk_proof: str):
    # # TODO: store messages to the DB
    # tx = None
    # if msg.initial_tx:
    #     tx = await crud.create_tx(msg.initial_tx)
    #
    # crud.create_approval(tx, uid, zkproof, msg)

    print(f'UID={uid} DATE={msg.date}')
    print(f'FROM={msg.member_email}')
    print(f'MSG_HASH={msg.msg_hash}')
    print(f'DKIM={msg.dkim_signature}')
    print(f'TX={msg.initial_tx}')
    print(f'ZKPROOF={zk_proof}')


async def send_response(msg: MemberMessage):
    await send_email(
        msg.member_email,
        subject='Relayer response',
        msg_text='Thank you for your message!',
    )


if __name__ == '__main__':
    db.init_db()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(idle_loop(IMAP_HOST, IMAP_PORT, RELAYER_EMAIL))
