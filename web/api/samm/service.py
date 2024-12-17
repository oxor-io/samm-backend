from api.conf import DEFAULT_EXPIRATION_PERIOD
from api.blockchain import fetch_samm_data
from api.samm.models import Samm
from api.samm.models import SammCreate


async def create_samm(samm_address: str, chain_id: int, name: str | None) -> Samm:
    # fetch samm params from blockchain
    safe_address, root, threshold = await fetch_samm_data(samm_address)
    samm_payload = SammCreate(
        name=name,
        samm_address=samm_address,
        safe_address=safe_address,
        threshold=threshold,
        expiration_period=DEFAULT_EXPIRATION_PERIOD,
        root=str(root),
        chain_id=chain_id,
        nonce=0,
        is_active=True,
    )
    return Samm.model_validate(samm_payload)

