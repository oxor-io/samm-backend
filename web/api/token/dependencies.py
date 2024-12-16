from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import SecurityScopes

from api.owner.models import Owner
from api.owner.crud import get_owner_by_address
from api.member.models import Member
from api.member.crud import get_member_by_email
from api.token.models import TokenData
from api.token.models import TokenScope
from api.token.models import TokenSubjectRole
from api.token.models import User
from api.token.utils import decode_jwt_access_token


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl='token',
    scopes={
        TokenScope.samm.value: 'Add/remove members',
        TokenScope.member.value: 'Get list of members/txns/SAMMs',
    }
)


async def get_token_subject(
        security_scopes: SecurityScopes,
        token: str = Depends(oauth2_scheme),
) -> User:
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

    subject: Owner | Member | None = None
    match token_data.role:
        case TokenSubjectRole.owner:
            subject = await get_owner_by_address(owner_address=token_data.sub_id)
        case TokenSubjectRole.member:
            subject = await get_member_by_email(member_email=token_data.sub_id)
        case _:
            pass

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate credentials',
            headers={'WWW-Authenticate': authenticate_value},
        )

    if not subject.is_active:
        raise HTTPException(status_code=400, detail='Inactive user')

    # check scopes
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Not enough permissions',
                headers={'WWW-Authenticate': authenticate_value},
            )

    return User(role=token_data.role, subject=subject)
