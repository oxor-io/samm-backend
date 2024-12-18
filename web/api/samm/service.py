from api.conf import DEFAULT_EXPIRATION_PERIOD
from api.samm.models import Samm
from api.samm.models import SammCreate


def create_samm(
        name: str | None,
        samm_address: str,
        safe_address: str,
        root: str,
        threshold: int,
        chain_id: int,
) -> Samm:
    samm_payload = SammCreate(
        name=name,
        samm_address=samm_address.lower(),
        safe_address=safe_address.lower(),
        threshold=threshold,
        expiration_period=DEFAULT_EXPIRATION_PERIOD,
        root=str(root),
        chain_id=chain_id,
        nonce=0,
        is_active=True,
    )
    return Samm.model_validate(samm_payload)

