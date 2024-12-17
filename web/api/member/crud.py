from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import engine
from api.member.models import Member


async def get_member_by_email(member_email: str) -> Member:
    async with AsyncSession(engine) as session:
        statement = select(Member).where(Member.email == member_email)
        results = await session.scalars(statement)
        return results.first()


async def save_members(members: list[Member]) -> list[Member]:
    async with AsyncSession(engine) as session:
        for member in members:
            session.add(member)
        await session.commit()

        for member in members:
            await session.refresh(member)
            print(f'NEW MEMBER SAVED: {member}, {member.hashed_password}')
        return members
