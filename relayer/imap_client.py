import aiohttp
import asyncio
import re
import logging
from itertools import batched

from aioimaplib import aioimaplib

import conf
from models import MailboxCursor
from member_message import parse_member_message
from member_message import store_member_message
from member_message import send_response
from prover import generate_zk_proof
from tx_execution import check_threshold
from tx_execution import execute_transaction
from tx_execution import change_transaction_status

# https://github.com/bamthomas/aioimaplib


# ID_HEADER_SET = 'Cc Content-Type In-Reply-To To Message-ID From Date References Subject Bcc DKIM-Signature'
# ID_HEADER_SET = 'From Date Subject DKIM-Signature'

FETCH_COMMAND = 'fetch'
# FETCH_CRITERIA_PARTS = 'FLAGS'
# FETCH_CRITERIA_PARTS = f'(UID FLAGS BODY.PEEK[HEADER.FIELDS ({ID_HEADER_SET})])'
FETCH_CRITERIA_PARTS = '(UID RFC822)'

FETCH_MESSAGE_DATA_SEQNUM = re.compile(rb'(?P<seqnum>\d+) FETCH.*')
FETCH_MESSAGE_DATA_UID = re.compile(rb'.*UID (?P<uid>\d+).*')
FETCH_MESSAGE_DATA_FLAGS = re.compile(rb'.*FLAGS \((?P<flags>.*?)\).*')

CHUNK_SIZE = 100

CURSORS = [
    # MailboxCursor(folder='Spam', uid_start=95, uid_end=95 + CHUNK_SIZE),
    MailboxCursor(folder='INBOX', uid_start=1, uid_end=540 + CHUNK_SIZE),
]


async def idle_loop():
    imap_client = await connect()

    cursor = CURSORS[0]
    switch_folder = True

    while True:
        try:
            if switch_folder:
                idx = CURSORS.index(cursor)
                cursor = CURSORS[0] if (idx + 1) >= len(CURSORS) else CURSORS[idx + 1]
                resp = await imap_client.select(cursor.folder)
                switch_folder = False
                print(f'Select mail folder: {cursor.folder}')

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

        except asyncio.TimeoutError:
            logging.exception(f'Timeout exception')
            raise asyncio.TimeoutError


async def connect() -> aioimaplib.IMAP4_SSL:
    imap_client = aioimaplib.IMAP4_SSL(host=conf.IMAP_HOST, port=conf.IMAP_PORT)
    resp = await imap_client.wait_hello_from_server()
    print(f'Hello server: {resp}')

    await authenticate_oauth_token(imap_client)

    return imap_client


async def authenticate_oauth_token(imap_client):
    token = await fetch_access_token(conf.GMAIL_REFRESH_TOKEN, conf.GMAIL_CLIENT_ID, conf.GMAIL_CLIENT_SECRET)
    resp = await imap_client.xoauth2(conf.RELAYER_EMAIL, token)
    print(f'Auth: {resp}')


async def fetch_access_token(refresh_token: str, client_id: str, client_secret: str) -> str:
    GOOGLE_API_URL = 'https://oauth2.googleapis.com/token'
    data = {
        'grant_type': 'refresh_token',
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'client_id': client_id,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url=GOOGLE_API_URL, data=data) as resp:
            print(f'refresh_access_token resp.status: {resp.status}')
            data = await resp.json()
            return data['access_token']


async def fetch_imap_messages(imap_client, uid_start: int, uid_end: int) -> int:
    resp = await imap_client.uid(FETCH_COMMAND, f'{uid_start}:{uid_end}', FETCH_CRITERIA_PARTS)
    print(f'Fetch mails UIDs={uid_start}:{uid_end} (lines={len(resp.lines)} / 3)')

    if resp.result != 'OK':
        print(f'Fetch command return an error: {resp}')
        raise

    uid_max = await process_imap_messages(resp.lines)
    print(f'Fetched uid_max={uid_max}')

    idle = await imap_client.idle_start(timeout=conf.IMAP_IDLE_TIMEOUT)
    print(f'IDLE: {idle.get_name()}')

    resp = await imap_client.wait_server_push()
    print(f'QUEUE: {resp}')

    imap_client.idle_done()

    await asyncio.wait_for(idle, 30)

    return uid_max


async def process_imap_messages(lines: list) -> int:
    uid_max = 0

    lines = lines[:-1]
    if rem := len(lines) % 3:
        print(f'Excess lines detected. All lines: {lines}')
        lines = lines[:len(lines) - rem]

    for start, raw_msg, end in batched(lines, 3):
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
            if not proof_struct:
                # TODO: send response that we could not generate proof
                pass
            else:
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
