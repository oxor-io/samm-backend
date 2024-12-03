from random import randint

from api.member import crud
from api.member.models import Member
from api.member.models import MemberCreateSecret
from api.member.utils import verify_password
from api.member.utils import get_password_hash
from api.member.utils import generate_merkle_tree


def create_member(member_email: str) -> Member:
    # TODO: merge secret and raw_password and(or) fix raw_password generation algorithm
    # TODO: send raw_password to the member_email
    secret = randint(1, 2048)
    raw_password = member_email + '_pass'

    member_payload = MemberCreateSecret(
        email=member_email,
        is_active=True,
        secret=secret,
        hashed_password=get_password_hash(raw_password),
    )
    return Member.model_validate(member_payload)


async def detect_and_save_new_members(member_emails: list[str]) -> tuple[list[Member], list[Member]]:
    members: list[Member] = []
    new_members: list[Member] = []

    for member_email in member_emails:
        member = await crud.get_member_by_email(member_email)
        if not member:
            member = create_member(member_email)
            new_members.append(member)
        members.append(member)

    await crud.save_members(new_members)
    return members, new_members


async def authenticate_member(member_email: str, member_raw_password: str) -> Member | None:
    member = await crud.get_member_by_email(member_email)
    if not member:
        return None
    if not verify_password(member_raw_password, member.hashed_password):
        return None
    return member


def calculate_samm_root(members: list[Member]) -> str:
    # TODO: check that the new(removed) member in the list
    emails_and_secrets = [(member.email, member.secret) for member in members]
    tree = generate_merkle_tree(emails_and_secrets)
    return str(tree.root)
