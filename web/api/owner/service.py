from web3.auto import w3
from eth_account.messages import encode_typed_data

from api.owner.models import Owner
from api.owner.models import OwnerCreate


def create_owner(owner_address: str) -> Owner:
    owner_payload = OwnerCreate(
        owner_address=owner_address,
        is_active=True,
    )
    return Owner.model_validate(owner_payload)


def check_signature(signature: str, chain_id: int, owner_address: str, samm_address: str, timestamp: int) -> bool:
    domain_data = {
        'name': 'SAMMAuthorizationRequest',
        'version': '1',
        'chainId': chain_id,
        'verifyingContract': samm_address,
        # 'salt': w3.solidity_keccak(['string'], ['SAMMAuthorizationRequest version: 1']).to_0x_hex(),
    }
    message_type = {
        'SAMMAuthorizationRequest': [
            {'name': 'signer', 'type': 'address'},
            {'name': 'module', 'type': 'address'},
            {'name': 'time', 'type': 'uint256'},
        ],
    }
    message_data = {
        'signer': owner_address,
        'module': samm_address,
        'time': timestamp,
    }

    msg = encode_typed_data(domain_data, message_type, message_data)
    signer_address = (w3.eth.account.recover_message(msg, signature=signature)).lower()
    return signer_address == owner_address


async def check_samm_owner(owner_address, samm_address) -> bool:
    # TODO:
    return True
