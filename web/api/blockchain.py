import os

from eth_typing import Address
from web3 import AsyncWeb3

from api.conf import SAMM_ABI

ADDRESS_SIZE = 20
RPC_URL = os.environ.get('RPC_URL')


async def fetch_samm_data(samm_address: str) -> tuple[str, int, int]:
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(RPC_URL))

    # samm_address = '96B4215538d1B838a6A452d6F50c02e7fA258f43'
    address = Address(int(samm_address, 16).to_bytes(length=ADDRESS_SIZE))
    contract_instance = w3.eth.contract(address=address, abi=SAMM_ABI)

    # https://github.com/oxor-io/samm-contracts/blob/master/src/SAMM.sol
    return (
        await contract_instance.functions.getSafe().call(),
        await contract_instance.functions.getMembersRoot().call(),
        await contract_instance.functions.getThreshold().call(),
    )
