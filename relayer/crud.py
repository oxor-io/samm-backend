from datetime import datetime
from datetime import timezone
from random import randint
from sqlmodel import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from db import engine
from models import Approval
from models import Member
from models import Samm
from models import Txn
from models import TxnStatus
from models import TxnOperation
from models import InitialData
from models import ProofStruct


DEFAULT_EXPIRATION_PERIOD = 30 * 24 * 60 * 60


async def create_txn(initial_data: InitialData) -> Txn:
    txn = Txn(
        msg_hash=initial_data.msg_hash,
        to=initial_data.txn_data.to,
        value=initial_data.txn_data.value,
        data=initial_data.txn_data.data,
        operation=initial_data.txn_data.operation,
        nonce=initial_data.txn_data.nonce,
        deadline=initial_data.txn_data.deadline,
        samm_id=initial_data.samm_id,
        status=TxnStatus.pending,
        created_at=datetime.now(),

        # NOTE: order is matter
        members=initial_data.members,
    )
    async with AsyncSession(engine) as session:
        session.add(txn)
        await session.commit()
        await session.refresh(txn)
        return txn


async def change_txn_status(txn_id: int, status: TxnStatus) -> Txn:
    async with AsyncSession(engine) as session:
        statement = select(Txn).where(Txn.id == txn_id)
        results = await session.scalars(statement)
        tx = results.one()

        tx.status = status
        session.add(tx)
        await session.commit()
        await session.refresh(tx)
        return tx


async def create_approval(txn: Txn, member: Member, proof_struct: ProofStruct, uid: int) -> Approval:
    approval = Approval(
        txn_id=txn.id,
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


async def get_members_by_txn(txn_id: int):
    async with AsyncSession(engine) as session:
        statement = select(Member).where(Member.txns.any(id=txn_id))
        results = await session.scalars(statement)
        return results.all()


async def get_member_by_email(member_email: str) -> Member:
    async with AsyncSession(engine) as session:
        statement = select(Member).where(Member.email == member_email.lower())
        results = await session.scalars(statement)
        return results.first()


async def get_txn_by_msg_hash(msg_hash: str) -> Txn:
    async with AsyncSession(engine) as session:
        statement = select(Txn).where(Txn.msg_hash == msg_hash).options(selectinload(Txn.samm))
        results = await session.scalars(statement)
        return results.first()


async def get_approval_by_uid(email_uid: int) -> Approval:
    async with AsyncSession(engine) as session:
        statement = select(Approval).where(Approval.email_uid == email_uid)
        results = await session.scalars(statement)
        return results.first()


async def get_approval_by_txn_and_email(txn_id: int, member_id: int) -> Approval:
    async with AsyncSession(engine) as session:
        statement = select(Approval).where(
            (Approval.txn_id == txn_id) & (Approval.member_id == member_id)
        )
        results = await session.scalars(statement)
        return results.first()


async def check_threshold_is_confirmed(txn_id: int, samm_id: int) -> bool:
    async with AsyncSession(engine) as session:
        # TODO: replace samm.threshold to tx.threshold at the moment of tx creation
        # TODO: refactor to single request
        statement = select(func.count('*')).where(
            (Approval.txn_id == txn_id)
        )
        approval_count = (await session.scalars(statement)).one()

        statement = select(Samm.threshold).where(
            (Samm.id == samm_id)
        )
        threshold = (await session.scalars(statement)).one()

        return approval_count >= threshold


async def get_approvals(txn_id: int):
    async with AsyncSession(engine) as session:
        statement = select(Approval).where(
            (Approval.txn_id == txn_id)
        )
        results = await session.scalars(statement)
        return results.all()


def _random_secret() -> str:
    return str(randint(
        1267650600228229401496703205377,
        21888242871839275222246405745257275088548364400416034343698204186575808495616
    ))


async def fill_db_initial_txn(first_user_email: str) -> Samm:
    async with AsyncSession(engine) as session:
        samm = Samm(
            name='FirstSAMM',
            samm_address='qwe123',
            safe_address='asd123',
            threshold=3,
            root='root',
            nonce=123,
            expiration_period=DEFAULT_EXPIRATION_PERIOD,
            chain_id=1,
            is_active=True,
        )

        m1 = Member(
            samm=samm,
            email=first_user_email,
            is_active=True,
            secret=_random_secret(),
            hashed_password='$2b$12$s6uvJVu5qdgj5vflGWgbburPUynFda5/B9GzJTWwAtZi/utv3CWNu',
        )
        m2 = Member(
            samm=samm,
            email='asd@gmail.com',
            is_active=True,
            secret=_random_secret(),
            hashed_password='$2b$12$OXgC3UOnGTSCN5YUvB956OJdDgbtJIwUWGtEmINxjtBXFXJIU7cOa',
        )
        m3 = Member(
            samm=samm,
            email='zxc@yandex.ru',
            is_active=True,
            secret=_random_secret(),
            hashed_password='$2b$12$DcAiu5KuPVQtxlFE6qGX7.VgOG7ioTXE21/DElx1zuheZ1cFKWwJ2',
        )
        m4 = Member(
            samm=samm,
            email='spammer@topdomain.xyz',
            is_active=False,
            secret=_random_secret(),
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


async def fill_db_approval_txn(first_user_email: str):
    async with AsyncSession(engine) as session:
        samm = Samm(
            name='FirstSAMM',
            samm_address='qwe123',
            safe_address='asd123',
            threshold=3,
            root='root',
            nonce=123,
            expiration_period=DEFAULT_EXPIRATION_PERIOD,
            chain_id=1,
            is_active=True,
        )

        m1 = Member(
            samm=samm,
            email=first_user_email,
            is_active=True,
            secret=_random_secret(),
            hashed_password='$2b$12$s6uvJVu5qdgj5vflGWgbburPUynFda5/B9GzJTWwAtZi/utv3CWNu',
        )
        m2 = Member(
            samm=samm,
            email='asd@gmail.com',
            is_active=True,
            secret=_random_secret(),
            hashed_password='$2b$12$OXgC3UOnGTSCN5YUvB956OJdDgbtJIwUWGtEmINxjtBXFXJIU7cOa',
        )
        m3 = Member(
            samm=samm,
            email='zxc@yandex.ru',
            is_active=True,
            secret=_random_secret(),
            hashed_password='$2b$12$DcAiu5KuPVQtxlFE6qGX7.VgOG7ioTXE21/DElx1zuheZ1cFKWwJ2',
        )
        m4 = Member(
            samm=samm,
            email='spammer@topdomain.xyz',
            is_active=False,
            secret=_random_secret(),
            hashed_password='$2b$12$ff97kTgAzfW8A7KlhR0r8e8Rt1NzVPmgiTwkBSei/lGM2XrlxWY6i',
        )

        txn = Txn(
            msg_hash='yxDnSnI6GTRsU2Dxol/UIeGesTpYQQhFPy4tuXF+W68=',
            to='0x1111',
            value=10**18,
            data=b'calldata',
            operation=TxnOperation.call,
            nonce=123,
            deadline=int(datetime(2025, 12, 31).replace(tzinfo=timezone.utc).timestamp()),
            root='root',
            samm=samm,
            status=TxnStatus.pending,
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

        txn.members.append(m1)
        txn.members.append(m2)
        txn.members.append(m3)
        txn.members.append(m4)
        session.add(txn)
        await session.commit()
