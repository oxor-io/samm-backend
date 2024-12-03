from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from fastapi import Query
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.token.dependencies import get_token_subject
from api.token.models import TokenScope
from api.transaction.models import Approval
from api.transaction.models import ApprovalPublic
from api.transaction.models import Transaction
from api.transaction.models import TransactionPublic
from api.transaction.models import TransactionStatus

router = APIRouter()


@router.get(
    '/samms/{samm_id}/transactions/',
    response_model=list[TransactionPublic],
    dependencies=[Security(get_token_subject, scopes=[TokenScope.member.value])],
)
async def get_transactions(
        samm_id: int,
        status: TransactionStatus,
        session: AsyncSession = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    # TODO: check samm_id in member.samms
    statement = select(Transaction).where(
        (Transaction.status == status) and (Transaction.samm_id == samm_id)
    ).offset(offset).limit(limit)
    transactions = (await session.scalars(statement)).all()
    return transactions


@router.get(
    '/transactions/{transaction_id}/approvals/',
    response_model=list[ApprovalPublic],
    dependencies=[Security(get_token_subject, scopes=[TokenScope.member.value])],
)
async def get_approvals(
        transaction_id: int,
        session: AsyncSession = Depends(get_session),
        offset: int = 0,
        limit: int = Query(default=100, le=100),
):
    # TODO: check transaction_id in member.transactions
    statement = select(Approval).where(Approval.transaction_id == transaction_id).offset(offset).limit(limit)
    approvals = (await session.scalars(statement)).all()
    return approvals
