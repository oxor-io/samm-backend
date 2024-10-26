#!/usr/bin/env python3
import os
from email.message import EmailMessage

from aiosmtplib import SMTP


# https://aiosmtplib.readthedocs.io/en/stable/quickstart.html

SMTP_HOST = os.environ.get('SMTP_HOST')
SMTP_PORT = os.environ.get('SMTP_PORT')
RELAYER_EMAIL = os.environ.get('RELAYER_EMAIL')
RELAYER_PASSWORD = os.environ.get('RELAYER_PASSWORD')


async def send_email(member_email: str, subject: str, msg_text: str):
    message = EmailMessage()
    message['From'] = RELAYER_EMAIL
    message['To'] = member_email
    message['Subject'] = subject
    message.set_content(msg_text)

    smtp_client = SMTP(
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=RELAYER_EMAIL,
        password=RELAYER_PASSWORD,
        use_tls=True
    )
    print('Create SMTP client')

    async with smtp_client:
        await smtp_client.send_message(message)
        print('Message sent')


# import asyncio
# asyncio.run(send_email(
#     member_email='test@gmail.com',
#     subject='Relayer response!',
#     msg_text='We have received the message!',
# ))

