from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import OAuth2PasswordRequestForm

from api.owner.crud import get_owner_by_address
from api.owner.crud import save_owner_and_samm
from api.owner.service import create_owner
from api.owner.service import check_signature
from api.owner.service import check_samm_owner
from api.samm.crud import get_samm_by_address
from api.samm.service import create_samm
from api.member.service import authenticate_member
from api.token.models import Token
from api.token.models import TokenScope
from api.token.models import TokenSubjectRole
from api.token.utils import encode_jwt_access_token

router = APIRouter()


@router.post('/token')
async def login_for_member_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    # authenticate member
    member = await authenticate_member(form_data.username, form_data.password)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    scopes = [TokenScope.member.value] if member.is_active else []

    # create access_token
    access_token = encode_jwt_access_token(
        role=TokenSubjectRole.member,
        sub_id=member.email,
        scopes=scopes,
    )
    return Token(access_token=access_token, token_type='bearer')


@router.post('/token/owner')
async def login_for_owner_access_token(
        owner_address: str,
        samm_address: str,
        chain_id: int,
        timestamp: int,
        signature: str,
):
    if not check_signature(signature, chain_id, owner_address, samm_address, timestamp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect signature',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    # check ownership in blockchain
    if not await check_samm_owner(owner_address, samm_address):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect owner of the SAMM',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    owner = await get_owner_by_address(owner_address)
    samm = await get_samm_by_address(samm_address)

    # new owner and samm
    if not owner:
        owner = create_owner(owner_address)
    if not samm:
        samm = await create_samm(samm_address, chain_id)

    await save_owner_and_samm(owner, samm)

    scopes = [TokenScope.member.value, TokenScope.samm.value] if owner.is_active else []

    # create access_token
    access_token = encode_jwt_access_token(
        role=TokenSubjectRole.owner,
        sub_id=owner_address,
        scopes=scopes,
    )
    return Token(access_token=access_token, token_type='bearer')
