from web3.auto import w3
from eth_account.messages import encode_typed_data

from api.owner import crud
from api.owner.models import Owner
from api.owner.models import OwnerCreate


def create_owner(owner_address: str) -> Owner:
    owner_payload = OwnerCreate(
        owner_address=owner_address.lower(),
        is_active=True,
    )
    return Owner.model_validate(owner_payload)


async def detect_and_save_new_owners(owner_addresses: list[str]) -> tuple[list[Owner], list[Owner]]:
    owners: list[Owner] = []
    new_owners: list[Owner] = []

    for owner_address in owner_addresses:
        owner = await crud.get_owner_by_address(owner_address)
        if not owner:
            owner = create_owner(owner_address)
            new_owners.append(owner)
        owners.append(owner)

    new_owners = await crud.save_owners(new_owners)
    return owners, new_owners


def check_signature(signature: str, chain_id: int, owner_address: str, samm_address: str, timestamp: int) -> bool:
    domain_data = {
        'name': 'SAMMAuthorizationRequest',
        'version': '1',
        'chainId': chain_id,
        'verifyingContract': samm_address.lower(),
    }
    message_type = {
        'SAMMAuthorizationRequest': [
            {'name': 'signer', 'type': 'address'},
            {'name': 'module', 'type': 'address'},
            {'name': 'time', 'type': 'uint256'},
        ],
    }
    message_data = {
        'signer': owner_address.lower(),
        'module': samm_address.lower(),
        'time': timestamp,
    }
    msg = encode_typed_data(domain_data, message_type, message_data)
    signer_address = (w3.eth.account.recover_message(msg, signature=signature)).lower()
    return signer_address.lower() == owner_address.lower()

