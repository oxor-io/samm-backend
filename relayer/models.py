from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel, Column
from pydantic import EmailStr
from sqlalchemy import String
from sqlalchemy import Enum as sa_Enum


class TransactionStatus(str, Enum):
    pending = 'pending'
    confirmed = 'confirmed'
    sent = 'sent'
    success = 'success'
    failed = 'failed'


class Member(SQLModel, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)
    email: EmailStr = Field(
        sa_type=String(),  # type: ignore[call-overload]
        unique=True,
        index=True,
        nullable=False,
        description='The email of the user',
    )
    # samm_id: int = Field(foreign_key='samm.id')
    is_active: bool


class Transaction(SQLModel, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)
    msg_hash: str
    to: str
    value: int
    data: str
    operation: str
    nonce: int
    # TODO: proof?
    proof: str
    # samm_id: int = Field(foreign_key='samm.id')
    # TODO: set default status
    status: TransactionStatus = Field(sa_column=Column(sa_Enum(TransactionStatus)))
    created_at: datetime


class Approval(SQLModel, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)
    transaction_id: int = Field(foreign_key='transaction.id')
    member_id: int = Field(foreign_key='member.id')
    proof: str
    created_at: datetime
    email_uid: int
