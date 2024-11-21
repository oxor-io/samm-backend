from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import engine
from api.models import Member


async def get_member_by_email(member_email: str) -> Member:
    async with AsyncSession(engine) as session:
        statement = select(Member).where(Member.email == member_email)
        results = await session.scalars(statement)
        return results.first()
