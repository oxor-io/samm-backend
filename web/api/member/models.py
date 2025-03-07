from pydantic import EmailStr
from sqlalchemy import String
from sqlmodel import Field
from sqlmodel import SQLModel
from sqlmodel import Relationship

from api.samm.models import Samm
from api.samm.models import SammMemberLink


# TODO: add indexes


class MemberTxnLink(SQLModel, table=True):
    member_id: int | None = Field(default=None, foreign_key='member.id', primary_key=True)
    txn_id: int | None = Field(default=None, foreign_key='txn.id', primary_key=True)


class MemberBase(SQLModel):
    email: EmailStr = Field(
        sa_type=String(),  # type: ignore[call-overload]
        unique=True,
        index=True,
        nullable=False,
        description="The email of the user",
    )


class Member(MemberBase, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)
    secret: str
    hashed_password: str
    is_active: bool

    samms: list[Samm] = Relationship(back_populates='members', link_model=SammMemberLink)
    txns: list['Txn'] = Relationship(back_populates='members', link_model=MemberTxnLink)
    approvals: list['Approval'] = Relationship(back_populates='member')


class MemberPublic(MemberBase):
    id: int
    is_active: bool


class MemberCreateSecret(MemberBase):
    secret: str
    hashed_password: str
    is_active: bool


class MemberRootPublic(SQLModel):
    root: str
