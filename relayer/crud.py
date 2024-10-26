from datetime import datetime
from sqlmodel import Session
from sqlmodel import select

from db import engine
from models import Approval
from models import Member
from models import Transaction
from models import TransactionStatus
from models import InitialData


async def create_tx(initial_data: InitialData) -> Transaction:
    tx = Transaction(
        msg_hash=initial_data.msg_hash,
        to=initial_data.tx_data.to,
        value=initial_data.tx_data.value,
        data=initial_data.tx_data.data,
        operation=initial_data.tx_data.operation,
        nonce=initial_data.tx_data.nonce,
        deadline_at=initial_data.tx_data.deadline,
        samm_id=initial_data.samm_id,
        status=TransactionStatus.pending,
        created_at=datetime.now(),

        # NOTE: order is matter
        members=initial_data.members,
    )
    with Session(engine) as session:
        session.add(tx)
        session.refresh(tx)
        session.commit()

    return tx


async def create_approval(tx: Transaction, member: Member, zk_proof: str, uid: int) -> Approval:
    approval = Approval(
        transaction_id=tx.id,
        member_id=member.id,
        proof=zk_proof,
        created_at=datetime.now(),
        email_uid=uid,
    )
    with Session(engine) as session:
        session.add(approval)
        session.refresh(approval)
        session.commit()

    return approval


async def get_members_by_samm(samm_id: int):
    with Session(engine) as session:
        statement = select(Member).where(Member.samm_id == samm_id)
        results = session.exec(statement)
        return results.all()


async def get_members_by_tx(tx_id: int):
    with Session(engine) as session:
        statement = select(Member).where(Member.transactions.any_(id=tx_id))
        results = session.exec(statement)
        return results.all()


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
            (Approval.transaction_id == tx_id) and (Approval.member_id == member_id)
        )
        results = session.exec(statement)
        return results.first()


# async def fill_db():
#     samm_id = 1
#     m1 = Member(samm_id=samm_id, email='vitalka.buterin@yandex.ru', is_active=True)
#     m2 = Member(samm_id=samm_id, email='asd@gmail.com', is_active=True)
#     m3 = Member(samm_id=samm_id, email='zxc@yandex.ru', is_active=True)
#     m4 = Member(samm_id=samm_id, email='spammer@topdomain.xyz', is_active=False)
#
#     tx = Transaction(
#         msg_hash='0xqweasdzxc123',
#         to='0x1111',
#         value=10**18,
#         data='calldata',
#         operation=TransactionOperation.call,
#         nonce=123,
#         deadline_at=datetime(2025, 12, 31),
#         root='root',
#         samm_id=samm_id,
#         status=TransactionStatus.pending,
#         created_at=datetime.now(),
#     )
#
#     with Session(engine) as session:
#         session.add(m1)
#         session.add(m2)
#         session.add(m3)
#         session.add(m4)
#
#         session.add(tx)
#
#         session.commit()