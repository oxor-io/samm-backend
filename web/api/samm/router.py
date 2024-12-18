from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from fastapi import HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.token.models import User
from api.token.models import TokenSubjectRole
from api.token.dependencies import get_token_subject
from api.samm.models import Samm
from api.samm.models import SammCreate
from api.samm.models import SammPublic
from api.token.models import TokenScope

router = APIRouter()


@router.get(
    '/samms/',
    response_model=list[SammPublic],
)
async def get_samms(
        session: AsyncSession = Depends(get_session),
        safe_address: str = None,
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    query = select(Samm)
    if safe_address:
        query = query.where(Samm.safe_address == safe_address.lower())
    statement = query.offset(offset).limit(limit)
    samms = (await session.scalars(statement)).all()
    return samms


@router.get(
    '/samms/me/',
    response_model=list[SammPublic],
)
async def get_samms_me(
        session: AsyncSession = Depends(get_session),
        user: User = Security(get_token_subject, scopes=[TokenScope.member.value]),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    if user.role == TokenSubjectRole.owner:
        statement = select(Samm).where(Samm.owners.any(id=user.subject.id)).offset(offset).limit(limit)
    elif user.role == TokenSubjectRole.member:
        statement = select(Samm).where(Samm.members.any(id=user.subject.id)).offset(offset).limit(limit)
    else:
        raise HTTPException(status_code=400, detail='Unexpected role')

    samms = (await session.scalars(statement)).all()
    return samms


@router.post(
    '/samms/',
    response_model=SammPublic,
    dependencies=[Security(get_token_subject, scopes=[TokenScope.samm.value])],
)
async def add_samm(
        samm_payload: SammCreate,
        session: AsyncSession = Depends(get_session),
):
    # TODO: check collision
    samm = Samm.model_validate(samm_payload)
    session.add(samm)
    await session.commit()
    await session.refresh(samm)
    return samm


@router.delete(
    '/samms/{samm_id}/',
    response_model=SammPublic,
    dependencies=[Security(get_token_subject, scopes=[TokenScope.samm.value])],
)
async def inactivate_samm(
        samm_id: int,
        session: AsyncSession = Depends(get_session),
):
    statement = select(Samm).where(Samm.id == samm_id)
    samm = (await session.scalars(statement)).one()

    samm.sqlmodel_update({
        'is_active': False,
    })
    session.add(samm)

    await session.commit()
    await session.refresh(samm)
    return samm
