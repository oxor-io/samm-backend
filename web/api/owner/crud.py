from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import engine
from api.owner.models import Owner
from api.samm.models import Samm
from sqlalchemy.orm import selectinload


async def get_owner_by_address(owner_address: str) -> Owner:
    async with AsyncSession(engine) as session:
        statement = select(Owner).where(Owner.owner_address == owner_address)
        results = await session.scalars(statement)
        return results.first()


async def save_owner_and_samm(owner: Owner, samm: Samm) -> tuple[Owner, Samm]:
    async with AsyncSession(engine) as session:
        session.add(owner)
        session.add(samm)
        await session.commit()
        await session.refresh(owner)
        await session.refresh(samm)

        # TODO: optimaze samm reloading
        statement = select(Samm).where(Samm.id == samm.id).options(selectinload(Samm.owners))
        samm = (await session.scalars(statement)).one()

        # add owner-samm relationship
        samm.owners.append(owner)
        session.add(samm)

        await session.commit()
        await session.refresh(owner)
        await session.refresh(samm)
        return owner, samm
