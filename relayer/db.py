from sqlmodel import create_engine, SQLModel


sqlite_file_name = 'database.db'
sqlite_url = f'sqlite:///{sqlite_file_name}'
connect_args = {'check_same_thread': False}
engine = create_engine(sqlite_url, connect_args=connect_args, echo=True)


# TODO: change database from sqlite to postgres
# import os
# DATABASE_URL = os.environ.get('DATABASE_URL')
# echo=True to see the generated SQL queries in the terminal
# engine = create_engine(DATABASE_URL, echo=True)


def init_db():
    # TODO: remove drop_all
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
