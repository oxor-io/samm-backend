from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from sqlmodel import select
from sqlmodel import Session

from api.db import get_session
from api.models import Samm
from api.models import SammCreate
from api.models import SammPublic
from api.models import Member
from api.models import MemberCreate
from api.models import MemberPublic

router = APIRouter()


@router.get('/samms', response_model=list[SammPublic])
def get_samms(
        session: Session = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    statement = select(Samm).offset(offset).limit(limit)
    samms = session.exec(statement).all()
    return samms


@router.post('/samms', response_model=SammPublic)
def add_samm(samm_payload: SammCreate, session: Session = Depends(get_session)):
    samm = Samm.model_validate(samm_payload)
    session.add(samm)
    session.commit()
    session.refresh(samm)
    return samm


@router.get('/members', response_model=list[MemberPublic])
def get_members(
        session: Session = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    statement = select(Member).offset(offset).limit(limit)
    members = session.exec(statement).all()
    return members


@router.post('/members', response_model=MemberPublic)
def add_member(member_payload: MemberCreate, session: Session = Depends(get_session)):
    # TODO: check SAMM existance
    member = Member.model_validate(member_payload)
    session.add(member)
    session.commit()
    session.refresh(member)
    return member
