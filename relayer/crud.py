from datetime import datetime
from datetime import timezone
from sqlmodel import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from db import engine
from models import Approval
from models import Member
from models import Samm
from models import Transaction
from models import TransactionStatus
from models import TransactionOperation
from models import InitialData
from models import ProofStruct


async def create_tx(initial_data: InitialData) -> Transaction:
    tx = Transaction(
        msg_hash=initial_data.msg_hash,
        to=initial_data.tx_data.to,
        value=initial_data.tx_data.value,
        data=initial_data.tx_data.data,
        operation=initial_data.tx_data.operation,
        nonce=initial_data.tx_data.nonce,
        deadline=initial_data.tx_data.deadline,
        samm_id=initial_data.samm_id,
        status=TransactionStatus.pending,
        created_at=datetime.now(),

        # NOTE: order is matter
        members=initial_data.members,
    )
    async with AsyncSession(engine) as session:
        session.add(tx)
        await session.commit()
        await session.refresh(tx)

    return tx


async def change_transaction_status(tx_id: int, status: TransactionStatus):
    # TODO:
    pass


async def create_approval(tx: Transaction, member: Member, proof_struct: ProofStruct, uid: int) -> Approval:
    approval = Approval(
        transaction_id=tx.id,
        member_id=member.id,
        proof=proof_struct.proof,
        commit=proof_struct.commit.to_bytes(32),
        domain=proof_struct.domain,
        pubkey_hash=proof_struct.pubkeyHash,
        is_2048_sig=proof_struct.is2048sig,
        created_at=datetime.now(),
        email_uid=uid,
    )
    async with AsyncSession(engine) as session:
        session.add(approval)
        await session.commit()
        await session.refresh(approval)

    return approval


async def get_members_by_samm(samm_id: int):
    async with AsyncSession(engine) as session:
        statement = select(Member).where(Member.samms.any(id=samm_id))
        results = await session.scalars(statement)
        return results.all()


async def get_members_by_tx(tx_id: int):
    async with AsyncSession(engine) as session:
        statement = select(Member).where(Member.transactions.any(id=tx_id))
        results = await session.scalars(statement)
        return results.all()


async def get_member_by_email(member_email: str) -> Member:
    async with AsyncSession(engine) as session:
        statement = select(Member).where(Member.email == member_email)
        results = await session.scalars(statement)
        return results.first()


async def get_tx_by_msg_hash(msg_hash: str) -> Transaction:
    async with AsyncSession(engine) as session:
        statement = select(Transaction).where(Transaction.msg_hash == msg_hash)
        results = await session.scalars(statement)
        return results.first()


async def get_approval_by_uid(email_uid: int) -> Approval:
    async with AsyncSession(engine) as session:
        statement = select(Approval).where(Approval.email_uid == email_uid)
        results = await session.scalars(statement)
        return results.first()


async def get_approval_by_tx_and_email(tx_id: int, member_id: int) -> Approval:
    async with AsyncSession(engine) as session:
        statement = select(Approval).where(
            (Approval.transaction_id == tx_id) and (Approval.member_id == member_id)
        )
        results = await session.scalars(statement)
        return results.first()


async def check_threshold_is_confirmed(tx_id: int, samm_id: int) -> bool:
    async with AsyncSession(engine) as session:
        # TODO: replace samm.threshold to tx.threshold at the moment of tx creation
        # TODO: refactor to single request
        statement = select(func.count('*')).where(
            (Approval.transaction_id == tx_id)
        )
        approval_count = (await session.scalars(statement)).one()

        statement = select(Samm.threshold).where(
            (Samm.id == samm_id)
        )
        threshold = (await session.scalars(statement)).one()

        return approval_count >= threshold


async def get_approvals(tx_id: int):
    async with AsyncSession(engine) as session:
        statement = select(Approval.proof).where(
            (Approval.transaction_id == tx_id)
        )
        results = await session.scalars(statement)
        return results.all()


async def fill_db_initial_tx(first_user_email: str) -> Samm:
    async with AsyncSession(engine) as session:
        samm = Samm(
            samm_address='qwe123',
            safe_address='asd123',
            threshold=3,
            root='root',
            nonce=123,
            expiration_period=int(datetime(2027, 1, 1).replace(tzinfo=timezone.utc).timestamp()),
            chain_id=1,
        )

        m1 = Member(
            samm=samm,
            email=first_user_email,
            is_active=True,
            is_admin=True,
            secret=111,
            hashed_password='$2b$12$s6uvJVu5qdgj5vflGWgbburPUynFda5/B9GzJTWwAtZi/utv3CWNu',
        )
        m2 = Member(
            samm=samm,
            email='asd@gmail.com',
            is_active=True,
            is_admin=False,
            secret=222,
            hashed_password='$2b$12$OXgC3UOnGTSCN5YUvB956OJdDgbtJIwUWGtEmINxjtBXFXJIU7cOa',
        )
        m3 = Member(
            samm=samm,
            email='zxc@yandex.ru',
            is_active=True,
            is_admin=False,
            secret=333,
            hashed_password='$2b$12$DcAiu5KuPVQtxlFE6qGX7.VgOG7ioTXE21/DElx1zuheZ1cFKWwJ2',
        )
        m4 = Member(
            samm=samm,
            email='spammer@topdomain.xyz',
            is_active=False,
            is_admin=False,
            secret=444,
            hashed_password='$2b$12$ff97kTgAzfW8A7KlhR0r8e8Rt1NzVPmgiTwkBSei/lGM2XrlxWY6i',
        )

        session.add(m1)
        session.add(m2)
        session.add(m3)
        session.add(m4)

        samm.members.append(m1)
        samm.members.append(m2)
        samm.members.append(m3)
        samm.members.append(m4)
        session.add(samm)

        await session.commit()
        await session.refresh(samm)
    return samm


async def fill_db_approval_tx(first_user_email: str):
    async with AsyncSession(engine) as session:
        samm = Samm(
            samm_address='qwe123',
            safe_address='asd123',
            threshold=3,
            root='root',
            nonce=123,
            expiration_period=int(datetime(2027, 1, 1).replace(tzinfo=timezone.utc).timestamp()),
            chain_id=1,
        )

        m1 = Member(
            samm=samm,
            email=first_user_email,
            is_active=True,
            is_admin=True,
            secret=111,
            hashed_password='$2b$12$s6uvJVu5qdgj5vflGWgbburPUynFda5/B9GzJTWwAtZi/utv3CWNu',
        )
        m2 = Member(
            samm=samm,
            email='asd@gmail.com',
            is_active=True,
            is_admin=False,
            secret=222,
            hashed_password='$2b$12$OXgC3UOnGTSCN5YUvB956OJdDgbtJIwUWGtEmINxjtBXFXJIU7cOa',
        )
        m3 = Member(
            samm=samm,
            email='zxc@yandex.ru',
            is_active=True,
            is_admin=False,
            secret=333,
            hashed_password='$2b$12$DcAiu5KuPVQtxlFE6qGX7.VgOG7ioTXE21/DElx1zuheZ1cFKWwJ2',
        )
        m4 = Member(
            samm=samm,
            email='spammer@topdomain.xyz',
            is_active=False,
            is_admin=False,
            secret=444,
            hashed_password='$2b$12$ff97kTgAzfW8A7KlhR0r8e8Rt1NzVPmgiTwkBSei/lGM2XrlxWY6i',
        )

        tx = Transaction(
            msg_hash='yxDnSnI6GTRsU2Dxol/UIeGesTpYQQhFPy4tuXF+W68=',
            to='0x1111',
            value=10**18,
            data=b'calldata',
            operation=TransactionOperation.call,
            nonce=123,
            deadline=int(datetime(2025, 12, 31).replace(tzinfo=timezone.utc).timestamp()),
            root='root',
            samm=samm,
            status=TransactionStatus.pending,
            created_at=datetime.now(),
        )
        session.add(m1)
        session.add(m2)
        session.add(m3)
        session.add(m4)

        samm.members.append(m1)
        samm.members.append(m2)
        samm.members.append(m3)
        samm.members.append(m4)
        session.add(samm)

        tx.members.append(m1)
        tx.members.append(m2)
        tx.members.append(m3)
        tx.members.append(m4)
        session.add(tx)
        await session.commit()
