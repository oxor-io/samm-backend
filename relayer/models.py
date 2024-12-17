from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel, Column
from pydantic import EmailStr
from sqlalchemy import BigInteger
from sqlalchemy import String
from sqlalchemy import Enum as sa_Enum
from sqlmodel import Relationship


class TxnOperation(str, Enum):
    call = 'CALL'
    delegate_call = 'DELEGATECALL'


class TxnStatus(str, Enum):
    pending = 'pending'
    confirmed = 'confirmed'
    sent = 'sent'
    success = 'success'
    failed = 'failed'


@dataclass
class Sequence:
    index: int
    length: int


class SammMemberLink(SQLModel, table=True):
    samm_id: int | None = Field(default=None, foreign_key='samm.id', primary_key=True)
    member_id: int | None = Field(default=None, foreign_key='member.id', primary_key=True)


class MemberTxnLink(SQLModel, table=True):
    member_id: int | None = Field(default=None, foreign_key='member.id', primary_key=True)
    txn_id: int | None = Field(default=None, foreign_key='txn.id', primary_key=True)


class SammOwnerLink(SQLModel, table=True):
    samm_id: int | None = Field(default=None, foreign_key='samm.id', primary_key=True)
    owner_id: int | None = Field(default=None, foreign_key='owner.id', primary_key=True)


class Owner(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner_address: str
    is_active: bool

    samms: list['Samm'] = Relationship(back_populates='owners', link_model=SammOwnerLink)


class Samm(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str | None
    nonce: int | None = Field(default=0)
    samm_address: str
    safe_address: str
    threshold: int
    expiration_period: int
    root: str
    chain_id: int
    is_active: bool

    owners: list[Owner] = Relationship(back_populates='samms', link_model=SammOwnerLink)
    members: list['Member'] = Relationship(back_populates='samms', link_model=SammMemberLink)
    txns: list['Txn'] = Relationship(back_populates='samm')


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
    hashed_password: str

    samms: list[Samm] = Relationship(back_populates='members', link_model=SammMemberLink)
    txns: list['Txn'] = Relationship(back_populates='members', link_model=MemberTxnLink)
    approvals: list['Approval'] = Relationship(back_populates='member')


class Txn(SQLModel, table=True):
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
    status: TxnStatus = Field(sa_column=Column(sa_Enum(TxnStatus)))
    created_at: datetime

    members: list[Member] = Relationship(back_populates='txns', link_model=MemberTxnLink)
    samm: Samm = Relationship(back_populates='txns')


class Approval(SQLModel, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)
    txn_id: int = Field(foreign_key='txn.id')
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
class TxnData:
    to: str
    value: int
    data: bytes
    operation: TxnOperation
    nonce: int
    deadline: int


@dataclass
class InitialData:
    samm_id: int
    msg_hash: str
    txn_data: TxnData
    members: list[Member]


@dataclass
class ApprovalData:
    domain: str
    header: list[int]
    header_length: int

    msg_hash: list[int]

    padded_member: list[int]
    padded_member_length: int
    secret: int
    padded_relayer: list[int]
    padded_relayer_length: int

    key_size: int
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
class ProofStruct:
    proof: bytes
    commit: int
    domain: str
    pubkeyHash: bytes  # NOTE: fixed bytes length
    is2048sig: bool


@dataclass
class MemberMessage:
    member: Member
    txn: Txn | None
    initial_data: InitialData | None
    approval_data: ApprovalData
