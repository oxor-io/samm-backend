from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.models import Samm
from api.models import SammCreate
from api.models import SammPublic
from api.models import Member
from api.models import MemberCreate
from api.models import MemberPublic
from api.models import Approval
from api.models import ApprovalPublic
from api.models import Transaction
from api.models import TransactionPublic

router = APIRouter()


@router.get('/samms', response_model=list[SammPublic])
async def get_samms(
        session: AsyncSession = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    statement = select(Samm).offset(offset).limit(limit)
    samms = (await session.scalars(statement)).all()
    return samms


@router.post('/samms', response_model=SammPublic)
async def add_samm(samm_payload: SammCreate, session: AsyncSession = Depends(get_session)):
    samm = Samm.model_validate(samm_payload)
    session.add(samm)
    await session.commit()
    await session.refresh(samm)
    return samm


@router.get('/members', response_model=list[MemberPublic])
async def get_members(
        session: AsyncSession = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    statement = select(Member).offset(offset).limit(limit)
    members = (await session.scalars(statement)).all()
    return members


@router.post('/members', response_model=MemberPublic)
async def add_member(member_payload: MemberCreate, session: AsyncSession = Depends(get_session)):
    # TODO: check SAMM existance
    member = Member.model_validate(member_payload)
    session.add(member)
    await session.commit()
    await session.refresh(member)
    return member


@router.get('/transactions', response_model=list[TransactionPublic])
async def get_transactions(
        session: AsyncSession = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    statement = select(Transaction).offset(offset).limit(limit)
    transactions = (await session.scalars(statement)).all()
    return transactions


@router.get('/approvals', response_model=list[ApprovalPublic])
async def get_approvals(
        session: AsyncSession = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    statement = select(Approval).offset(offset).limit(limit)
    approvals = (await session.scalars(statement)).all()
    return approvals
