import os
from dotenv import load_dotenv

SECRETS_FILE = os.environ.get('SECRETS_FILE')
load_dotenv(SECRETS_FILE or '.env_web')

DATABASE_URL = os.environ.get('DATABASE_URL')
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
