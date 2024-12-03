from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.db import engine
from api.samm.models import Samm


async def get_samm_by_address(samm_address: str) -> Samm:
    async with AsyncSession(engine) as session:
        statement = select(Samm).where(Samm.samm_address == samm_address).options(selectinload(Samm.owners))
        results = await session.scalars(statement)
        return results.first()


async def update_members_and_root(samm_id: int, root: str, members):
    async with AsyncSession(engine) as session:
        statement = select(Samm).where(Samm.id == samm_id).options(selectinload(Samm.members))
        samm = (await session.scalars(statement)).one()

        # TODO: reorder samm.members by member_emails list

        exclude_members = [member for member in samm.members if member not in members]
        for member in exclude_members:
            samm.members.remove(member)

        include_members = [member for member in members if member not in samm.members]
        for member in include_members:
            samm.members.append(member)

        # update samm root
        samm.sqlmodel_update({
            'root': root,
        })
        session.add(samm)

        await session.commit()
        await session.refresh(samm)
