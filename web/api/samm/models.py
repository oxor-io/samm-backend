from sqlmodel import Field
from sqlmodel import SQLModel
from sqlmodel import Relationship

from api.owner.models import Owner
from api.owner.models import SammOwnerLink


# TODO: add indexes


class SammMemberLink(SQLModel, table=True):
    samm_id: int | None = Field(default=None, foreign_key='samm.id', primary_key=True)
    member_id: int | None = Field(default=None, foreign_key='member.id', primary_key=True)


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

    owners: list[Owner] = Relationship(back_populates='samms', link_model=SammOwnerLink)
    members: list['Member'] = Relationship(back_populates='samms', link_model=SammMemberLink)
    transactions: list['Transaction'] = Relationship(back_populates='samm')


class SammPublic(SammBase):
    id: int
    nonce: int


class SammCreate(SammBase):
    pass

