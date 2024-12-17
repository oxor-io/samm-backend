from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from fastapi import Query
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.token.dependencies import get_token_subject
from api.token.models import TokenScope
from api.txn.models import Approval
from api.txn.models import ApprovalPublic
from api.txn.models import Txn
from api.txn.models import TxnPublic
from api.txn.models import TxnStatus

router = APIRouter()


@router.get(
    '/samms/{samm_id}/transactions/',
    response_model=list[TxnPublic],
    dependencies=[Security(get_token_subject, scopes=[TokenScope.member.value])],
)
async def get_txns(
        samm_id: int,
        status: TxnStatus | None = None,
        session: AsyncSession = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    # TODO: check samm_id in member.samms
    condition = (Txn.samm_id == samm_id)
    if status:
        condition &= (Txn.status == status)
    statement = select(Txn).where(condition).offset(offset).limit(limit)
    txns = (await session.scalars(statement)).all()
    return txns


@router.get(
    '/transactions/{txn_id}/approvals/',
    response_model=list[ApprovalPublic],
    dependencies=[Security(get_token_subject, scopes=[TokenScope.member.value])],
)
async def get_approvals(
        txn_id: int,
        session: AsyncSession = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    # TODO: check txn_id in member.txns
    statement = select(Approval).where(Approval.txn_id == txn_id).offset(offset).limit(limit)
    approvals = (await session.scalars(statement)).all()
    return approvals
