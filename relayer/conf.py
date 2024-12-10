import os
from dotenv import load_dotenv

SECRETS_FILE = os.environ.get('SECRETS_FILE')
load_dotenv(SECRETS_FILE or '.env_relayer')


IMAP_HOST = os.environ.get('IMAP_HOST')
IMAP_PORT = os.environ.get('IMAP_PORT')
IMAP_IDLE_TIMEOUT = os.environ.get('IMAP_IDLE_TIMEOUT')
RELAYER_EMAIL = os.environ.get('RELAYER_EMAIL')

GMAIL_REFRESH_TOKEN = os.environ.get('GMAIL_REFRESH_TOKEN')
GMAIL_CLIENT_ID = os.environ.get('GMAIL_CLIENT_ID')
GMAIL_CLIENT_SECRET = os.environ.get('GMAIL_CLIENT_SECRET')
