from sqlmodel import Session
from sqlmodel import select

from db import engine
from models import Approval
from models import Member
from models import Transaction


async def create_tx() -> Transaction:
    pass


async def create_approval() -> Approval:
    pass


async def get_member_by_email(member_email: str) -> Member:
    with Session(engine) as session:
        statement = select(Member).where(Member.email == member_email)
        results = session.exec(statement)
        return results.first()


async def get_tx_by_msg_hash(msg_hash: str) -> Transaction:
    with Session(engine) as session:
        statement = select(Transaction).where(Transaction.msg_hash == msg_hash)
        results = session.exec(statement)
        return results.first()


async def get_approval_by_uid(email_uid: int) -> Approval:
    with Session(engine) as session:
        statement = select(Approval).where(Approval.email_uid == email_uid)
        results = session.exec(statement)
        return results.first()


async def get_approval_by_tx_and_email(tx_id: int, member_id: int) -> Approval:
    with Session(engine) as session:
        statement = select(Approval).where(
            (Approval.tx_id == tx_id) and (Approval.member_id == member_id)
        )
        results = session.exec(statement)
        return results.first()
