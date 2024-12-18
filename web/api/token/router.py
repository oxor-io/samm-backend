from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import OAuth2PasswordRequestForm

from api import blockchain
from api.owner.service import check_signature
from api.owner.service import detect_and_save_new_owners
from api.samm.crud import get_samm_by_address
from api.samm.crud import save_samm
from api.samm.crud import update_owners
from api.samm.service import create_samm
from api.member.service import authenticate_member
from api.token.models import Token
from api.token.models import TokenScope
from api.token.models import TokenSubjectRole
from api.token.utils import encode_jwt_access_token

router = APIRouter()


@router.post('/token')
@router.post('/token/')
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


@router.post('/token/owner/')
async def login_for_owner_access_token(
        owner_address: str,
        samm_address: str,
        chain_id: int,
        timestamp: int,
        signature: str,
        name: str | None = None,
):
    owner_address = owner_address.lower()
    samm_address = samm_address.lower()

    if not check_signature(signature, chain_id, owner_address, samm_address, timestamp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect signature',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    # fetch samm's blockchain info
    samm = await get_samm_by_address(samm_address)
    if samm:
        safe_address, root, threshold = samm.safe_address, samm.root, samm.threshold
    else:
        safe_address, root, threshold = await blockchain.fetch_samm_data(samm_address)

    if not safe_address:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect SAMM address',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    # check ownership in blockchain
    owner_addresses = await blockchain.get_safe_owners(safe_address)
    if not owner_addresses:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect Safe address',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    if owner_address not in owner_addresses:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect owner of the SAMM',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    # create new samm
    if not samm:
        samm = create_samm(name, samm_address, safe_address, root, threshold, chain_id)
        samm = await save_samm(samm)

    # create new owners
    owners, new_owners = await detect_and_save_new_owners(owner_addresses)

    # update relationships samm<->owners
    await update_owners(samm.id, owners)

    # find current owner from owners
    current_owner = None
    for owner in owners:
        if owner.owner_address == owner_address and owner.is_active:
            current_owner = owner
            break

    scopes = [TokenScope.member.value, TokenScope.samm.value] if current_owner.is_active else []

    # create access_token
    access_token = encode_jwt_access_token(
        role=TokenSubjectRole.owner,
        sub_id=owner_address,
        scopes=scopes,
    )
    return Token(access_token=access_token, token_type='bearer')
