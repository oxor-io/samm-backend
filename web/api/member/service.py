import secrets
from random import randint

from api.sender import send_email
from api.member import crud
from api.member.models import Member
from api.member.models import MemberCreateSecret
from api.member.utils import verify_password
from api.member.utils import get_password_hash
from api.member.utils import generate_merkle_tree


def create_member(member_email: str) -> tuple[Member, str]:
    # TODO: merge secret and raw_password
    secret = randint(1, 2048)
    raw_password = secrets.token_urlsafe(8)
    hashed_password = get_password_hash(raw_password)
    member_payload = MemberCreateSecret(
        email=member_email,
        is_active=True,
        secret=secret,
        hashed_password=hashed_password,
    )
    print(f'CREATE NEW MEMBER: {member_email}, {raw_password}, {hashed_password}')
    return Member.model_validate(member_payload), raw_password


async def detect_and_save_new_members(member_emails: list[str]) -> tuple[list[Member], list[Member]]:
    members: list[Member] = []
    new_members: list[Member] = []
    member_email_and_password: list[tuple[str, str]] = []

    for member_email in member_emails:
        member = await crud.get_member_by_email(member_email)
        if not member:
            member, raw_password = create_member(member_email)
            member_email_and_password.append((member.email, raw_password))
            new_members.append(member)
        members.append(member)

    new_members = await crud.save_members(new_members)

    for member_email, raw_password in member_email_and_password:
        await send_email(
            member_email,
            subject='Member password in SAMM',
            msg_text=f'You have been added to participate in SAMM. Your password: {raw_password}',
        )
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
    # TODO: less predictable order
    members.sort(key=lambda x: x.id)
    emails_and_secrets = [(member.email, member.secret) for member in members]
    tree = generate_merkle_tree(emails_and_secrets)
    return str(tree.root)
