import os
from dotenv import load_dotenv

SECRETS_FILE = os.environ.get('SECRETS_FILE')
load_dotenv(SECRETS_FILE or '.env_relayer')

INIT_DATABASE = bool(os.environ.get('INIT_DATABASE'))

IMAP_HOST = os.environ.get('IMAP_HOST')
IMAP_PORT = os.environ.get('IMAP_PORT')
IMAP_IDLE_TIMEOUT = int(os.environ.get('IMAP_IDLE_TIMEOUT'))
RELAYER_EMAIL = os.environ.get('RELAYER_EMAIL')

RELAYER_ADDRESS = os.environ.get('RELAYER_ADDRESS')

GMAIL_REFRESH_TOKEN = os.environ.get('GMAIL_REFRESH_TOKEN')
GMAIL_CLIENT_ID = os.environ.get('GMAIL_CLIENT_ID')
GMAIL_CLIENT_SECRET = os.environ.get('GMAIL_CLIENT_SECRET')

SAMM_APP_URL = os.environ.get('SAMM_APP_URL')