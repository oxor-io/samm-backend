from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel, Column
from pydantic import EmailStr
from sqlalchemy import BigInteger
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


class SammMemberLink(SQLModel, table=True):
    samm_id: int | None = Field(default=None, foreign_key='samm.id', primary_key=True)
    member_id: int | None = Field(default=None, foreign_key='member.id', primary_key=True)


class MemberTransactionLink(SQLModel, table=True):
    member_id: int | None = Field(default=None, foreign_key='member.id', primary_key=True)
    transaction_id: int | None = Field(default=None, foreign_key='transaction.id', primary_key=True)


class Samm(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nonce: int | None = Field(default=0)
    samm_address: str
    safe_address: str
    threshold: int
    expiration_period: int
    root: str
    chain_id: int

    members: list['Member'] = Relationship(back_populates='samms', link_model=SammMemberLink)
    transactions: list['Transaction'] = Relationship(back_populates='samm')


class Member(SQLModel, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)
    email: EmailStr = Field(
        sa_type=String(),  # type: ignore[call-overload]
        unique=True,
        index=True,
        nullable=False,
        description='The email of the user',
    )
    is_active: bool
    secret: int

    samms: list[Samm] = Relationship(back_populates='members', link_model=SammMemberLink)
    transactions: list['Transaction'] = Relationship(back_populates='members', link_model=MemberTransactionLink)
    approvals: list['Approval'] = Relationship(back_populates='member')


class Transaction(SQLModel, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)
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

    members: list[Member] = Relationship(back_populates='transactions', link_model=MemberTransactionLink)
    samm: Samm = Relationship(back_populates='transactions')


class Approval(SQLModel, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)
    transaction_id: int = Field(foreign_key='transaction.id')
    member_id: int = Field(foreign_key='member.id')
    proof: bytes
    commit: bytes   # NOTE: fixed size
    domain: str
    pubkey_hash: bytes  # NOTE: fixed size
    is_2048_sig: bool
    created_at: datetime
    email_uid: int

    member: Member = Relationship(back_populates='approvals')


@dataclass
class MailboxCursor:
    folder: str
    uid_start: int
    uid_end: int


@dataclass
class TxData:
    to: str
    value: int
    data: bytes
    operation: TransactionOperation
    nonce: int
    deadline: int


@dataclass
class InitialData:
    samm_id: int
    msg_hash: str
    tx_data: TxData
    members: list[Member]


@dataclass
class ApprovalData:
    domain: str
    header: list[int]
    header_length: int

    msg_hash: list[int]

    padded_member: list[int]
    padded_member_length: int
    padded_relayer: list[int]
    padded_relayer_length: int

    key_size: int
    pubkey_modulus_limbs: list[str]
    redc_params_limbs: list[str]
    signature: list[str]

    root: str
    path_elements: list[str]
    path_indices: list[int]


@dataclass
class ProofStruct:
    proof: bytes
    commit: int
    domain: str
    pubkeyHash: bytes  # NOTE: fixed bytes length
    is2048sig: bool


@dataclass
class MemberMessage:
    member: Member
    tx: Transaction | None
    initial_data: InitialData | None
    approval_data: ApprovalData
