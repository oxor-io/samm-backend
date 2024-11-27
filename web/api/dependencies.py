from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi import Security
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import SecurityScopes

from api.models import Member
from api.crud import get_member_by_email
from api.token.models import TokenData
from api.token.models import TokenScope
from api.token.utils import decode_jwt_access_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl='token',
    scopes={
        TokenScope.samm.value: 'Add/remove members, get/add SAMMs',
        TokenScope.member.value: 'Get list of members/transactions',
    }
)


async def get_current_member(
        security_scopes: SecurityScopes,
        token: str = Depends(oauth2_scheme),
):
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = 'Bearer'

    token_data: TokenData = decode_jwt_access_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token',
            headers={'WWW-Authenticate': authenticate_value},
        )

    # check member
    member = await get_member_by_email(member_email=token_data.member_email)
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate credentials',
            headers={'WWW-Authenticate': authenticate_value},
        )

    # check scopes
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Not enough permissions',
                headers={'WWW-Authenticate': authenticate_value},
            )
    return member


async def get_current_active_member(
        member: Member = Security(get_current_member, scopes=[TokenScope.member.value]),
) -> Member:
    if not member.is_active:
        raise HTTPException(status_code=400, detail='Inactive user')
    return member
