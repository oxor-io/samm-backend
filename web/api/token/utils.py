from datetime import datetime
from datetime import timedelta
from datetime import timezone

import jwt
from jwt.exceptions import InvalidTokenError

from api.conf import JWT_SECRET_KEY
from api.conf import JWT_ALGORITHM
from api.conf import JWT_ACCESS_TOKEN_EXPIRE_MINUTES
from api.token.models import TokenData


def encode_jwt_access_token(member_email: str, scopes: list[str]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES or 15)
    token_data = TokenData(member_email=member_email, scopes=scopes, exp=expire)
    encoded_jwt = jwt.encode(token_data.__dict__, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_jwt_access_token(token: str) -> TokenData | None:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        member_email: str = payload.get('member_email')
        if member_email is None:
            return None
        scopes: list[str] = payload.get('scopes')
        token_data = TokenData(member_email=member_email, scopes=scopes, exp=None)
    except InvalidTokenError:
        return None
    return token_data
