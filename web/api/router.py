from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from pydantic import EmailStr
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.db import get_session
from api.dependencies import get_current_active_member
from api.models import Samm
from api.models import SammCreate
from api.models import SammPublic
from api.models import Member
from api.models import MemberPublic
from api.models import Approval
from api.models import ApprovalPublic
from api.models import Transaction
from api.models import TransactionPublic
from api.models import TransactionStatus
from api.service import create_member
from api.token.models import TokenScope

router = APIRouter()


@router.get(
    '/samms/',
    response_model=list[SammPublic],
    # dependencies=[Security(get_current_active_member, scopes=[TokenScope.samm.value])],
)
async def get_samms(
        session: AsyncSession = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    statement = select(Samm).offset(offset).limit(limit)
    samms = (await session.scalars(statement)).all()
    return samms


@router.post(
    '/samms/',
    response_model=SammPublic,
    # dependencies=[Security(get_current_active_member, scopes=[TokenScope.samm.value])],
)
async def add_samm(
        samm_payload: SammCreate,
        session: AsyncSession = Depends(get_session),
):
    samm = Samm.model_validate(samm_payload)
    session.add(samm)
    await session.commit()
    await session.refresh(samm)
    return samm


@router.get(
    '/samms/{samm_id}/members',
    response_model=list[MemberPublic],
    # dependencies=[Depends(get_current_active_member)]
)
async def get_samm_members(
        samm_id: int,
        session: AsyncSession = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    statement = select(Member).where(Member.samms.any(id=samm_id)).offset(offset).limit(limit)
    members = (await session.scalars(statement)).all()
    return members


@router.post(
    '/samms/{samm_id}/members/',
    response_model=MemberPublic,
    # dependencies=[Security(get_current_active_member, scopes=[TokenScope.samm.value])],
)
async def add_samm_members(
        samm_id: int,
        member_email: EmailStr,
        session: AsyncSession = Depends(get_session),
):
    statement = select(Samm).where(Samm.id == samm_id)
    samm = (await session.scalars(statement)).one()

    statement = select(Member).where(Member.email == member_email)
    member = (await session.scalars(statement)).first()

    if not member:
        member = create_member(member_email)

    # TODO: recalculate samm.root

    member.samms.append(samm)
    session.add(member)
    await session.commit()
    await session.refresh(member)
    return member


@router.delete(
    '/samms/{samm_id}/members/',
    response_model=MemberPublic,
    # dependencies=[Security(get_current_active_member, scopes=[TokenScope.samm.value])],
)
async def remove_samm_members(
        samm_id: int,
        member_email: EmailStr,
        session: AsyncSession = Depends(get_session),
):
    statement = select(Samm).where(Samm.id == samm_id)
    samm = (await session.scalars(statement)).one()

    statement = select(Member).where(Member.email == member_email).options(selectinload(Member.samms))
    member = (await session.scalars(statement)).one()

    # TODO: recalculate samm.root

    member.samms.remove(samm)
    session.add(member)
    await session.commit()
    return member


@router.get(
    '/samms/{samm_id}/transactions/',
    response_model=list[TransactionPublic],
    # dependencies=[Depends(get_current_active_member)],
)
async def get_transactions(
        samm_id: int,
        status: TransactionStatus,
        session: AsyncSession = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    statement = select(Transaction).where(
        (Transaction.status == status) and (Transaction.samm_id == samm_id)
    ).offset(offset).limit(limit)
    transactions = (await session.scalars(statement)).all()
    return transactions


@router.get(
    '/transactions/{transaction_id}/approvals/',
    response_model=list[ApprovalPublic],
    # dependencies=[Depends(get_current_active_member)],
)
async def get_approvals(
        transaction_id: int,
        session: AsyncSession = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    statement = select(Approval).where(Approval.transaction_id == transaction_id).offset(offset).limit(limit)
    approvals = (await session.scalars(statement)).all()
    return approvals


@router.get('/member_ping', dependencies=[Depends(get_current_active_member)])
async def member_ping():
    return {'ping': 'pong!'}


@router.get('/samm_ping', dependencies=[Security(get_current_active_member, scopes=[TokenScope.samm.value])],)
async def samm_ping():
    return {'ping': 'pong!'}
