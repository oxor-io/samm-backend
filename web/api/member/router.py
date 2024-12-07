from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from pydantic import EmailStr
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.member.models import Member
from api.member.models import MemberPublic
from api.member.models import MemberRootPublic
from api.member.service import calculate_samm_root
from api.member.service import detect_and_save_new_members
from api.samm.crud import update_members_and_root
from api.token.dependencies import get_token_subject
from api.token.models import TokenScope


router = APIRouter()


@router.post(
    '/members/root/',
    response_model=MemberRootPublic,
)
async def get_samm_root(
        member_emails: list[EmailStr],
):
    members, new_members = await detect_and_save_new_members(member_emails)
    return MemberRootPublic(root=calculate_samm_root(members))


@router.get(
    '/samms/{samm_id}/members/',
    response_model=list[MemberPublic],
    dependencies=[Security(get_token_subject, scopes=[TokenScope.member.value])],
)
async def get_samm_members(
        samm_id: int,
        session: AsyncSession = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    # TODO: only samm owner has access to samm.members list
    statement = select(Member).where(Member.samms.any(id=samm_id)).offset(offset).limit(limit)
    members = (await session.scalars(statement)).all()
    return members


@router.post(
    '/samms/{samm_id}/members/',
    response_model=list[MemberPublic],
    dependencies=[Security(get_token_subject, scopes=[TokenScope.samm.value])],
    # dependencies=[Security(get_token_subject, scopes=[TokenScope.member.value])],
)
async def add_samm_members(
        samm_id: int,
        member_emails: list[str],
):
    # TODO: only samm owner has access to samm.members list

    members, new_members = await detect_and_save_new_members(member_emails)
    root = calculate_samm_root(members)

    await update_members_and_root(samm_id, root, members)
    return members


# @router.post(
#     '/samms/{samm_id}/members/',
#     response_model=MemberPublic,
#     dependencies=[Security(get_token_subject, scopes=[TokenScope.samm.value])],
# )
# async def add_samm_members(
#         samm_id: int,
#         member_email: EmailStr,
#         session: AsyncSession = Depends(get_session),
# ):
#     statement = select(Samm).where(Samm.id == samm_id).options(selectinload(Samm.members))
#     samm = (await session.scalars(statement)).one()
#
#     statement = select(Member).where(Member.email == member_email)
#     member = (await session.scalars(statement)).first()
#
#     if not member:
#         member = create_member(member_email)
#
#     member.samms.append(samm)
#     session.add(member)
#
#     # update samm root
#     samm.sqlmodel_update({
#         'root': calculate_samm_root(samm.members)
#     })
#     session.add(samm)
#
#     await session.commit()
#     await session.refresh(member)
#     return member


# @router.delete(
#     '/samms/{samm_id}/members/',
#     response_model=MemberPublic,
#     dependencies=[Security(get_token_subject, scopes=[TokenScope.samm.value])],
# )
# async def remove_samm_members(
#         samm_id: int,
#         member_email: EmailStr,
#         session: AsyncSession = Depends(get_session),
# ):
#     statement = select(Samm).where(Samm.id == samm_id)
#     samm = (await session.scalars(statement)).one()
#
#     statement = select(Member).where(Member.email == member_email).options(selectinload(Member.samms))
#     member = (await session.scalars(statement)).one()
#
#     member.samms.remove(samm)
#     session.add(member)
#
#     # update samm root
#     samm.sqlmodel_update({
#         'root': calculate_samm_root(samm.members)
#     })
#     session.add(samm)
#
#     await session.commit()
#     return member
