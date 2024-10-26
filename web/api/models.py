from pydantic import EmailStr
from sqlalchemy import String
from sqlmodel import Field
from sqlmodel import SQLModel
from sqlmodel import Relationship


# TODO: add indexes


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

    members: list["Member"] = Relationship(back_populates='samm')


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
    samm_id: int = Field(foreign_key="samm.id")
    is_active: bool


class Member(MemberBase, table=True):
    id: int | None = Field(default=None, nullable=False, primary_key=True)
    secret: int

    samm: Samm = Relationship(back_populates='members')


class MemberPublic(MemberBase):
    id: int


class MemberCreate(MemberBase):
    secret: int
    # TODO: is_active?
