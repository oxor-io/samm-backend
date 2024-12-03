from sqlmodel import Field
from sqlmodel import SQLModel
from sqlmodel import Relationship


class SammOwnerLink(SQLModel, table=True):
    samm_id: int | None = Field(default=None, foreign_key='samm.id', primary_key=True)
    owner_id: int | None = Field(default=None, foreign_key='owner.id', primary_key=True)


class OwnerBase(SQLModel):
    # TODO: the same address for different chain_id?
    owner_address: str
    is_active: bool


class Owner(OwnerBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    samms: list['Samm'] = Relationship(back_populates='owners', link_model=SammOwnerLink)


class OwnerPublic(OwnerBase):
    id: int


class OwnerCreate(OwnerBase):
    pass
