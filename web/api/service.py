from random import randint

from api.crud import get_member_by_email
from api.models import Member
from api.models import MemberCreateSecret
from api.utils import verify_password
from api.utils import get_password_hash


def create_member(member_email: str) -> Member:
    # TODO: merge secret and raw_password and(or) fix raw_password generation algorithm
    # TODO: send raw_password to the member_email
    secret = randint(1, 2048)
    raw_password = member_email + '_pass'

    member_payload = MemberCreateSecret(
        email=member_email,
        is_active=True,
        is_admin=False,
        secret=secret,
        hashed_password=get_password_hash(raw_password),
    )
    return Member.model_validate(member_payload)


async def authenticate_member(member_email: str, member_raw_password: str) -> Member | None:
    member = await get_member_by_email(member_email)
    if not member:
        return None
    if not verify_password(member_raw_password, member.hashed_password):
        return None
    return member
