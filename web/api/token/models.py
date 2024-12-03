from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from api.owner.models import Owner
from api.member.models import Member


class TokenSubjectRole(str, Enum):
    owner = 'owner'
    member = 'member'


class TokenScope(str, Enum):
    member = 'member'
    samm = 'samm'


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    role: TokenSubjectRole
    sub_id: str
    exp: datetime | None
    scopes: list[str]


class User(BaseModel):
    role: TokenSubjectRole
    subject: Owner | Member
