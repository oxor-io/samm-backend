from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class TokenScope(str, Enum):
    member = 'member'
    samm = 'samm'


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    member_email: str
    exp: datetime | None
    scopes: list[str]
