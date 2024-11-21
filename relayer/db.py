import os
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine


DATABASE_URL = os.environ.get('DATABASE_URL')


if DATABASE_URL and 'postgresql' in DATABASE_URL:
    # echo=True to see the generated SQL queries in the terminal
    engine = create_async_engine(DATABASE_URL, echo=True)
else:
    DATABASE_URL = 'sqlite+aiosqlite:///database.db'
    connect_args = {'check_same_thread': False}
    engine = create_async_engine(DATABASE_URL, connect_args=connect_args, echo=True)


async def init_db():
    async with engine.begin() as conn:
        # TODO: remove drop_all before release
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

