from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel, Column
from pydantic import EmailStr
from sqlalchemy import String
from sqlalchemy import Enum as sa_Enum
from sqlmodel import Relationship


class TransactionOperation(str, Enum):
    call = 'CALL'
    delegate_call = 'DELEGATECALL'


class TransactionStatus(str, Enum):
    pending = 'pending'
    confirmed = 'confirmed'
    sent = 'sent'
    success = 'success'
    failed = 'failed'

@dataclass
class Sequence:
    index: int
    length: int

class Samm(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nonce: int | None = Field(default=0)
    samm_address: str
    safe_address: str
    threshold: int
    expiration_period: int
    root: str
    chain_id: int

    members: list['Member'] = Relationship(back_populates='samm')


class MemberTransactionLink(SQLModel, table=True):
    member_id: int | None = Field(default=None, foreign_key='member.id', primary_key=True)
    transaction_id: int | None = Field(default=None, foreign_key='transaction.id', primary_key=True)


class Member(SQLModel, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)
    email: EmailStr = Field(
        sa_type=String(),  # type: ignore[call-overload]
        unique=True,
        index=True,
        nullable=False,
        description='The email of the user',
    )
    samm_id: int = Field(foreign_key='samm.id')
    is_active: bool
    secret: int

    samm: Samm = Relationship(back_populates='members')
    transactions: list['Transaction'] = Relationship(back_populates='members', link_model=MemberTransactionLink)


class Transaction(SQLModel, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)
    msg_hash: str
    to: str
    value: int
    data: str
    operation: str
    nonce: int
    deadline_at: datetime
    samm_id: int = Field(foreign_key='samm.id')
    # TODO: set default status
    status: TransactionStatus = Field(sa_column=Column(sa_Enum(TransactionStatus)))
    created_at: datetime

    members: list[Member] = Relationship(back_populates='transactions', link_model=MemberTransactionLink)


class Approval(SQLModel, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)
    transaction_id: int = Field(foreign_key='transaction.id')
    member_id: int = Field(foreign_key='member.id')
    proof: str
    created_at: datetime
    email_uid: int


@dataclass
class TxData:
    to: str
    value: int
    data: str
    operation: TransactionOperation
    nonce: int
    deadline: datetime


@dataclass
class InitialData:
    samm_id: int
    msg_hash: str
    tx_data: TxData
    members: list[Member]


@dataclass
class ApprovalData:
    header: list[int]
    header_length: int

    msg_hash: list[int]

    padded_member: list[int]
    padded_member_length: int
    secret: int
    padded_relayer: list[int]
    padded_relayer_length: int

    pubkey_modulus_limbs: list[str]
    redc_params_limbs: list[str]
    signature: list[str]

    root: str
    path_elements: list[str]
    path_indices: list[int]

    from_seq: Sequence
    member_seq: Sequence
    to_seq: Sequence
    relayer_seq: Sequence


@dataclass
class MemberMessage:
    member: Member
    tx: Transaction
    initial_data: InitialData
    approval_data: ApprovalData


@dataclass
class MessageAttributes:
    uid: int
    # flags: list[str]
    sequence_number: int
    member_message: MemberMessage | None
