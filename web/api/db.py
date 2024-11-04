import os
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession

# sqlite_file_name = 'database.db'
# sqlite_url = f'sqlite:///{sqlite_file_name}'
# connect_args = {'check_same_thread': False}
# engine = create_engine(sqlite_url, connect_args=connect_args)

DATABASE_URL = os.environ.get('DATABASE_URL')
# echo=True to see the generated SQL queries in the terminal
engine = create_async_engine(DATABASE_URL, echo=True)


async def init_db():
    async with engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncSession:
    async_session = AsyncSession(engine, expire_on_commit=False)
    async with async_session as session:
        yield session
