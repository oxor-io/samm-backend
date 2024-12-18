import logging
import os

from eth_typing import Address
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from api.conf import SAMM_ABI
from api.conf import SAFE_ABI

ADDRESS_SIZE = 20
RPC_URL = os.environ.get('RPC_URL')


async def fetch_samm_data(samm_address: str) -> tuple[str, int, int]:
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(RPC_URL))

    address = Address(int(samm_address, 16).to_bytes(length=ADDRESS_SIZE))
    contract_instance = w3.eth.contract(address=address, abi=SAMM_ABI)

    # https://github.com/oxor-io/samm-contracts/blob/master/src/SAMM.sol
    try:
        safe_address = await contract_instance.functions.getSafe().call()
        root = await contract_instance.functions.getMembersRoot().call()
        threshold = await contract_instance.functions.getThreshold().call()
    except Web3Exception as ex:
        logging.exception(f'Web3 exception with samm={samm_address}: ')
        safe_address, root, threshold = '', 0, 0

    return safe_address, root, threshold


async def get_safe_owners(safe_address: str) -> list[str]:
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(RPC_URL))

    address = Address(int(safe_address, 16).to_bytes(length=ADDRESS_SIZE))
    contract_instance = w3.eth.contract(address=address, abi=SAFE_ABI)

    # https://github.com/safe-global/safe-smart-account/blob/main/contracts/base/OwnerManager.sol#L133
    try:
        owner_address = await contract_instance.functions.getOwners().call()
    except Web3Exception as ex:
        logging.exception(f'Web3 exception with safe={safe_address}: ')
        owner_address = []

    return [address.lower() for address in owner_address]
