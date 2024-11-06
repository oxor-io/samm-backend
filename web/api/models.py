from datetime import datetime
from enum import Enum
from pydantic import EmailStr
from sqlalchemy import BigInteger
from sqlalchemy import String
from sqlalchemy import Enum as sa_Enum
from sqlmodel import Column
from sqlmodel import Field
from sqlmodel import SQLModel
from sqlmodel import Relationship


# TODO: add indexes

class SammMemberLink(SQLModel, table=True):
    samm_id: int | None = Field(default=None, foreign_key='samm.id', primary_key=True)
    member_id: int | None = Field(default=None, foreign_key='member.id', primary_key=True)


class MemberTransactionLink(SQLModel, table=True):
    member_id: int | None = Field(default=None, foreign_key='member.id', primary_key=True)
    transaction_id: int | None = Field(default=None, foreign_key='transaction.id', primary_key=True)


class SammBase(SQLModel):
    samm_address: str
    safe_address: str
    threshold: int
    expiration_period: int
    root: str
    chain_id: int


class Samm(SammBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nonce: int | None = Field(default=0)

    members: list['Member'] = Relationship(back_populates='samms', link_model=SammMemberLink)
    transactions: list['Transaction'] = Relationship(back_populates='samm')


class SammPublic(SammBase):
    id: int
    nonce: int


class SammCreate(SammBase):
    pass


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
    secret: int
    is_active: bool

    samms: list[Samm] = Relationship(back_populates='members', link_model=SammMemberLink)
    transactions: list['Transaction'] = Relationship(back_populates='members', link_model=MemberTransactionLink)
    approvals: list['Approval'] = Relationship(back_populates='member')


class MemberPublic(MemberBase):
    id: int
    is_active: bool


class MemberCreateSecret(MemberBase):
    secret: int
    is_active: bool


# Models from Relayer


class TransactionOperation(str, Enum):
    call = 'CALL'
    delegate_call = 'DELEGATECALL'


class TransactionStatus(str, Enum):
    pending = 'pending'
    confirmed = 'confirmed'
    sent = 'sent'
    success = 'success'
    failed = 'failed'


class TransactionBase(SQLModel):
    msg_hash: str
    to: str
    value: int = Field(sa_column=Column(BigInteger()))
    data: str
    operation: str
    nonce: int
    deadline: int = Field(sa_column=Column(BigInteger()))
    samm_id: int = Field(foreign_key='samm.id')
    # TODO: set default status
    status: TransactionStatus = Field(sa_column=Column(sa_Enum(TransactionStatus)))
    created_at: datetime


class Transaction(TransactionBase, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)

    members: list[Member] = Relationship(back_populates='transactions', link_model=MemberTransactionLink)
    samm: Samm = Relationship(back_populates='transactions')


class TransactionPublic(TransactionBase):
    id: int


class ApprovalBase(SQLModel):
    transaction_id: int = Field(foreign_key='transaction.id')
    proof: str
    created_at: datetime


class Approval(ApprovalBase, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)
    member_id: int = Field(foreign_key='member.id')
    email_uid: int

    member: Member = Relationship(back_populates='approvals')


class ApprovalPublic(ApprovalBase):
    id: int
