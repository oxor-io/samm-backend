from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import OAuth2PasswordRequestForm

from api.service import authenticate_member
from api.token.models import Token
from api.token.models import TokenScope
from api.token.utils import encode_jwt_access_token

router = APIRouter()


@router.post('/token')
async def login_for_access_token(
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

    # detect scope list
    if member.is_admin:
        scopes = [TokenScope.member.value, TokenScope.samm.value]
    elif member.is_active:
        scopes = [TokenScope.member.value]
    else:
        scopes = []

    # create access_token
    access_token = encode_jwt_access_token(
        member_email=member.email,
        scopes=scopes,
    )
    return Token(access_token=access_token, token_type='bearer')

