from datetime import datetime
from enum import Enum
from pydantic import field_serializer
from sqlalchemy import BigInteger
from sqlalchemy import Enum as sa_Enum
from sqlmodel import Column
from sqlmodel import Field
from sqlmodel import SQLModel
from sqlmodel import Relationship

from api.samm.models import Samm
from api.member.models import Member
from api.member.models import MemberTransactionLink


# TODO: add indexes
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
    data: bytes
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
    proof: bytes
    commit: bytes
    domain: str
    pubkey_hash: bytes
    is_2048_sig: bool
    created_at: datetime


class Approval(ApprovalBase, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)
    member_id: int = Field(foreign_key='member.id')
    email_uid: int

    member: Member = Relationship(back_populates='approvals')


class ApprovalPublic(ApprovalBase):
    id: int

    @field_serializer('commit')
    def serialize_commit(self, commit: bytes):
        return int.from_bytes(commit)

    @field_serializer('pubkey_hash')
    def serialize_pubkey_hash(self, pubkey_hash: bytes):
        # int(pubkey_hash, 16).to_bytes(length=32),
        return hex(int.from_bytes(pubkey_hash))
