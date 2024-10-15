from sqlmodel import create_engine, SQLModel, Session


sqlite_file_name = 'database.db'
sqlite_url = f'sqlite:///{sqlite_file_name}'
connect_args = {'check_same_thread': False}
engine = create_engine(sqlite_url, connect_args=connect_args)


# TODO: change database from sqlite to postgres 
# import os
# DATABASE_URL = os.environ.get('DATABASE_URL')
# echo=True to see the generated SQL queries in the terminal
# engine = create_engine(DATABASE_URL, echo=True)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
