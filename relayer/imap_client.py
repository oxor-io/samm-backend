import aiohttp
import asyncio
import re
from itertools import batched

from aioimaplib import aioimaplib

import conf
from models import MailboxCursor
from member_message import parse_member_message
from member_message import process_member_message
from member_message import send_response_by_member_message
from logger import logger

# https://github.com/bamthomas/aioimaplib


FETCH_COMMAND = 'fetch'
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
                logger.info(f'Select mail folder: {cursor.folder}')

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
            logger.exception(f'Timeout exception')
            raise asyncio.TimeoutError


async def connect() -> aioimaplib.IMAP4_SSL:
    imap_client = aioimaplib.IMAP4_SSL(host=conf.IMAP_HOST, port=conf.IMAP_PORT)
    resp = await imap_client.wait_hello_from_server()
    logger.info(f'Hello server: {resp}')

    await authenticate_oauth_token(imap_client)

    return imap_client


async def authenticate_oauth_token(imap_client):
    token = await fetch_access_token(conf.GMAIL_REFRESH_TOKEN, conf.GMAIL_CLIENT_ID, conf.GMAIL_CLIENT_SECRET)
    resp = await imap_client.xoauth2(conf.RELAYER_EMAIL, token)
    logger.info(f'Auth: {resp}')


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
            logger.info(f'Refresh access_token, resp.status: {resp.status}')
            data = await resp.json()
            return data['access_token']


async def fetch_imap_messages(imap_client, uid_start: int, uid_end: int) -> int:
    resp = await imap_client.uid(FETCH_COMMAND, f'{uid_start}:{uid_end}', FETCH_CRITERIA_PARTS)
    logger.info(f'Fetch mails UIDs={uid_start}:{uid_end} (lines={len(resp.lines)} / 3)')

    if resp.result != 'OK':
        logger.error(f'Fetch command return an error: {resp}')
        raise

    uid_max = await process_imap_messages(resp.lines)
    logger.info(f'Fetched uid_max={uid_max}')

    idle = await imap_client.idle_start(timeout=conf.IMAP_IDLE_TIMEOUT)
    logger.info(f'IDLE: {idle.get_name()}')

    resp = await imap_client.wait_server_push()
    logger.info(f'Queue: {resp}')

    imap_client.idle_done()

    await asyncio.wait_for(idle, 30)

    return uid_max


async def process_imap_messages(lines: list) -> int:
    uid_max = 0

    lines = lines[:-1]
    if rem := len(lines) % 3:
        logger.warning(f'Excess lines detected. All lines: {lines}')
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

        try:
            logger.info(f'====== Parse raw message: UID={uid}')
            member_message = await parse_member_message(uid, raw_msg)
            if member_message:
                logger.info(f'Process member message')
                is_confirmed, txn = await process_member_message(uid, member_message)
                if txn:
                    logger.info(f'Send response by member message')
                    await send_response_by_member_message(member_message, txn, is_confirmed)
        except:
            logger.exception('Member message processing is failed')

        if uid > uid_max:
            uid_max = uid

    return uid_max
