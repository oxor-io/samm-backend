from datetime import datetime
from datetime import timedelta
from datetime import timezone

import jwt
from jwt.exceptions import InvalidTokenError

from api.conf import JWT_SECRET_KEY
from api.conf import JWT_ALGORITHM
from api.conf import JWT_ACCESS_TOKEN_EXPIRE_MINUTES
from api.token.models import TokenData
from api.token.models import TokenSubjectRole


def encode_jwt_access_token(role: TokenSubjectRole, sub_id: str, scopes: list[str]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES or 15)
    sub = role.value + sub_id
    token_data = TokenData(
        sub=sub,
        role=role,
        sub_id=sub_id,
        scopes=scopes,
        exp=expire
    )
    encoded_jwt = jwt.encode(token_data.__dict__, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_jwt_access_token(token: str) -> TokenData | None:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        scopes: list[str] = payload.get('scopes')
        role = payload.get('role')
        sub_id: str = payload.get('sub_id')

        if role is None or sub_id is None:
            return None

        return TokenData(role=role, sub_id=sub_id, scopes=scopes, exp=None)
    except InvalidTokenError:
        return None
