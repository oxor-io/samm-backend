from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import engine
from api.owner.models import Owner


async def get_owner_by_address(owner_address: str) -> Owner:
    async with AsyncSession(engine) as session:
        statement = select(Owner).where(Owner.owner_address == owner_address.lower())
        results = await session.scalars(statement)
        return results.first()


async def save_owner(owner: Owner) -> Owner:
    async with AsyncSession(engine) as session:
        session.add(owner)
        await session.commit()
        await session.refresh(owner)
        return owner


async def save_owners(owners: list[Owner]) -> list[Owner]:
    async with AsyncSession(engine) as session:
        for owner in owners:
            session.add(owner)
        await session.commit()

        for owner in owners:
            await session.refresh(owner)
            print(f'NEW OWNER SAVED: {owner}')
        return owners
