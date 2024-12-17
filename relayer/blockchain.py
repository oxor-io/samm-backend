import os

from eth_typing import Address
from web3 import AsyncWeb3
from web3.middleware import SignAndSendRawMiddlewareBuilder
from web3.exceptions import ContractCustomError
from web3.types import TxReceipt

from logger import logger
from models import ProofStruct
from models import TxnData
from models import TxnOperation
from utils import without_0x

ADDRESS_SIZE = 20
RPC_URL = os.environ.get('RPC_URL')
PRIVATE_KEY = os.environ.get('PRIVATE_KEY')

# TODO: replace to json file
SAMM_ABI = '[{"type":"constructor","inputs":[],"stateMutability":"nonpayable"},{"type":"function","name":"allowance","inputs":[{"name":"to","type":"address","internalType":"address"}],"outputs":[{"name":"","type":"uint256","internalType":"uint256"}],"stateMutability":"view"},{"type":"function","name":"executeTransaction","inputs":[{"name":"to","type":"address","internalType":"address"},{"name":"value","type":"uint256","internalType":"uint256"},{"name":"data","type":"bytes","internalType":"bytes"},{"name":"operation","type":"uint8","internalType":"enum IMinimalSafeModuleManager.Operation"},{"name":"proofs","type":"tuple[]","internalType":"struct ISAMM.Proof[]","components":[{"name":"proof","type":"bytes","internalType":"bytes"},{"name":"commit","type":"uint256","internalType":"uint256"},{"name":"domain","type":"string","internalType":"string"},{"name":"pubkeyHash","type":"bytes32","internalType":"bytes32"},{"name":"is2048sig","type":"bool","internalType":"bool"}]},{"name":"deadline","type":"uint256","internalType":"uint256"}],"outputs":[{"name":"success","type":"bool","internalType":"bool"}],"stateMutability":"nonpayable"},{"type":"function","name":"executeTransactionReturnData","inputs":[{"name":"to","type":"address","internalType":"address"},{"name":"value","type":"uint256","internalType":"uint256"},{"name":"data","type":"bytes","internalType":"bytes"},{"name":"operation","type":"uint8","internalType":"enum IMinimalSafeModuleManager.Operation"},{"name":"proofs","type":"tuple[]","internalType":"struct ISAMM.Proof[]","components":[{"name":"proof","type":"bytes","internalType":"bytes"},{"name":"commit","type":"uint256","internalType":"uint256"},{"name":"domain","type":"string","internalType":"string"},{"name":"pubkeyHash","type":"bytes32","internalType":"bytes32"},{"name":"is2048sig","type":"bool","internalType":"bool"}]},{"name":"deadline","type":"uint256","internalType":"uint256"}],"outputs":[{"name":"success","type":"bool","internalType":"bool"},{"name":"returnData","type":"bytes","internalType":"bytes"}],"stateMutability":"nonpayable"},{"type":"function","name":"getDKIMRegistry","inputs":[],"outputs":[{"name":"dkimRegistry","type":"address","internalType":"address"}],"stateMutability":"view"},{"type":"function","name":"getMembersRoot","inputs":[],"outputs":[{"name":"root","type":"uint256","internalType":"uint256"}],"stateMutability":"view"},{"type":"function","name":"getMessageHash","inputs":[{"name":"to","type":"address","internalType":"address"},{"name":"value","type":"uint256","internalType":"uint256"},{"name":"data","type":"bytes","internalType":"bytes"},{"name":"operation","type":"uint8","internalType":"enum IMinimalSafeModuleManager.Operation"},{"name":"nonce","type":"uint256","internalType":"uint256"},{"name":"deadline","type":"uint256","internalType":"uint256"}],"outputs":[{"name":"msgHash","type":"bytes32","internalType":"bytes32"}],"stateMutability":"view"},{"type":"function","name":"getNonce","inputs":[],"outputs":[{"name":"nonce","type":"uint256","internalType":"uint256"}],"stateMutability":"view"},{"type":"function","name":"getRelayer","inputs":[],"outputs":[{"name":"relayer","type":"string","internalType":"string"}],"stateMutability":"view"},{"type":"function","name":"getSafe","inputs":[],"outputs":[{"name":"safe","type":"address","internalType":"address"}],"stateMutability":"view"},{"type":"function","name":"getThreshold","inputs":[],"outputs":[{"name":"threshold","type":"uint64","internalType":"uint64"}],"stateMutability":"view"},{"type":"function","name":"isTxAllowed","inputs":[{"name":"to","type":"address","internalType":"address"},{"name":"selector","type":"bytes4","internalType":"bytes4"}],"outputs":[{"name":"","type":"bool","internalType":"bool"}],"stateMutability":"view"},{"type":"function","name":"setAllowance","inputs":[{"name":"to","type":"address","internalType":"address"},{"name":"amount","type":"uint256","internalType":"uint256"}],"outputs":[],"stateMutability":"nonpayable"},{"type":"function","name":"setDKIMRegistry","inputs":[{"name":"dkimRegistry","type":"address","internalType":"address"}],"outputs":[],"stateMutability":"nonpayable"},{"type":"function","name":"setMembersRoot","inputs":[{"name":"membersRoot","type":"uint256","internalType":"uint256"}],"outputs":[],"stateMutability":"nonpayable"},{"type":"function","name":"setRelayer","inputs":[{"name":"relayer","type":"string","internalType":"string"}],"outputs":[],"stateMutability":"nonpayable"},{"type":"function","name":"setThreshold","inputs":[{"name":"threshold","type":"uint64","internalType":"uint64"}],"outputs":[],"stateMutability":"nonpayable"},{"type":"function","name":"setTxAllowed","inputs":[{"name":"to","type":"address","internalType":"address"},{"name":"selector","type":"bytes4","internalType":"bytes4"},{"name":"isAllowed","type":"bool","internalType":"bool"}],"outputs":[],"stateMutability":"nonpayable"},{"type":"function","name":"setup","inputs":[{"name":"safe","type":"address","internalType":"address"},{"name":"membersRoot","type":"uint256","internalType":"uint256"},{"name":"threshold","type":"uint64","internalType":"uint64"},{"name":"relayer","type":"string","internalType":"string"},{"name":"dkimRegistry","type":"address","internalType":"address"},{"name":"txAllowances","type":"tuple[]","internalType":"struct ISAMM.TxAllowance[]","components":[{"name":"to","type":"address","internalType":"address"},{"name":"selector","type":"bytes4","internalType":"bytes4"},{"name":"amount","type":"uint256","internalType":"uint256"}]}],"outputs":[],"stateMutability":"nonpayable"},{"type":"event","name":"AllowanceChanged","inputs":[{"name":"to","type":"address","indexed":true,"internalType":"address"},{"name":"amount","type":"uint256","indexed":false,"internalType":"uint256"}],"anonymous":false},{"type":"event","name":"DKIMRegistryIsChanged","inputs":[{"name":"dkimRegistry","type":"address","indexed":false,"internalType":"address"}],"anonymous":false},{"type":"event","name":"MembersRootIsChanged","inputs":[{"name":"newRoot","type":"uint256","indexed":false,"internalType":"uint256"}],"anonymous":false},{"type":"event","name":"RelayerIsChanged","inputs":[{"name":"relayer","type":"string","indexed":false,"internalType":"string"}],"anonymous":false},{"type":"event","name":"Setup","inputs":[{"name":"initiator","type":"address","indexed":true,"internalType":"address"},{"name":"safe","type":"address","indexed":true,"internalType":"address"},{"name":"initialSetupRoot","type":"uint256","indexed":false,"internalType":"uint256"},{"name":"threshold","type":"uint64","indexed":false,"internalType":"uint64"},{"name":"relayer","type":"string","indexed":false,"internalType":"string"},{"name":"dkimRegistry","type":"address","indexed":false,"internalType":"address"}],"anonymous":false},{"type":"event","name":"ThresholdIsChanged","inputs":[{"name":"threshold","type":"uint64","indexed":false,"internalType":"uint64"}],"anonymous":false},{"type":"event","name":"TxAllowanceChanged","inputs":[{"name":"to","type":"address","indexed":true,"internalType":"address"},{"name":"selector","type":"bytes4","indexed":false,"internalType":"bytes4"},{"name":"isAllowed","type":"bool","indexed":false,"internalType":"bool"}],"anonymous":false},{"type":"error","name":"SAMM__DKIMPublicKeyVerificationFailed","inputs":[{"name":"commitIndex","type":"uint256","internalType":"uint256"}]},{"type":"error","name":"SAMM__allowanceIsNotEnough","inputs":[]},{"type":"error","name":"SAMM__alreadyInitialized","inputs":[]},{"type":"error","name":"SAMM__commitAlreadyUsed","inputs":[{"name":"usedCommitIndex","type":"uint256","internalType":"uint256"}]},{"type":"error","name":"SAMM__deadlineIsPast","inputs":[]},{"type":"error","name":"SAMM__dkimRegistryIsZero","inputs":[]},{"type":"error","name":"SAMM__emptyRelayer","inputs":[]},{"type":"error","name":"SAMM__longRelayer","inputs":[]},{"type":"error","name":"SAMM__noChanges","inputs":[]},{"type":"error","name":"SAMM__notEnoughProofs","inputs":[{"name":"amountOfGivenProofs","type":"uint256","internalType":"uint256"},{"name":"threshold","type":"uint256","internalType":"uint256"}]},{"type":"error","name":"SAMM__notSafe","inputs":[]},{"type":"error","name":"SAMM__proofVerificationFailed","inputs":[{"name":"failedProofIndex","type":"uint256","internalType":"uint256"}]},{"type":"error","name":"SAMM__rootIsZero","inputs":[]},{"type":"error","name":"SAMM__safeIsZero","inputs":[]},{"type":"error","name":"SAMM__thresholdIsZero","inputs":[]},{"type":"error","name":"SAMM__toIsWrong","inputs":[]},{"type":"error","name":"SAMM__txIsNotAllowed","inputs":[]}]'


def convert_address_from_str(address: str) -> Address:
    return Address(
        int(without_0x(address), 16).to_bytes(length=ADDRESS_SIZE)
    )


async def execute_txn(
        samm_address: str,
        txn_data: TxnData,
        proof_structs: list[ProofStruct]
) -> tuple[bool, TxReceipt | None]:
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(RPC_URL))
    # await w3.is_connected()

    acc = w3.eth.account.from_key(PRIVATE_KEY)
    w3.middleware_onion.inject(SignAndSendRawMiddlewareBuilder.build(acc), layer=0)

    # samm_address = '478dC0AF4ABf508b9Cf21004D891C34632FA9986'
    address = convert_address_from_str(samm_address)
    contract_instance = w3.eth.contract(address=address, abi=SAMM_ABI)

    logger.info(f'Transaction txn_data: {txn_data}')
    logger.info(f'Transaction proof_structs: {proof_structs}')

    for proof_struct in proof_structs:
        proof_struct.proof = bytes.fromhex(proof_struct.proof.decode())

    # address to,
    # uint256 value,
    # bytes memory data,
    # ISafe.Operation operation,
    # Proof[] calldata proofs,
    # uint256 deadline
    params = (
        convert_address_from_str(txn_data.to),
        txn_data.value,
        bytes.fromhex(without_0x(txn_data.data.decode())),
        list(TxnOperation).index(txn_data.operation),
        [proof.__dict__ for proof in proof_structs],
        txn_data.deadline,
    )

    # TODO: add try-cache network exceptions
    try:
        txn_hash = await contract_instance.functions.executeTransactionReturnData(*params).transact({'from': acc.address})
    except ContractCustomError:
        logger.exception('ContractCustomError: ')
        return False, None

    # Wait for the transaction to be mined, and get the transaction receipt
    txn_receipt = await w3.eth.wait_for_transaction_receipt(txn_hash, timeout=180)
    if not txn_receipt:
        return True, None

    # TODO: check reorg

    # TODO: check receipt(must return success)
    # if receipt_returned_True:
    success = True

    return success, txn_receipt


async def get_message_hash(
        samm_address: str,
        to: str,
        value: int,
        data: str,
        operation: int,
        nonce: int,
        deadline: int
) -> bytes:
    """
        params = {
            'to': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
            'value': 0,
            'data': '0x18160ddd',
            'operation': 0,
            'nonce': 0,
            'deadline': 4884818384,
        }
        msg_hash_raw: bytes = await get_message_hash('0x478dC0AF4ABf508b9Cf21004D891C34632FA9986', **params)
    """
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(RPC_URL))
    # await w3.is_connected()

    acc = w3.eth.account.from_key(PRIVATE_KEY)
    w3.middleware_onion.inject(SignAndSendRawMiddlewareBuilder.build(acc), layer=0)

    address = convert_address_from_str(samm_address)
    contract_instance = w3.eth.contract(address=address, abi=SAMM_ABI)

    params = (
        convert_address_from_str(to),
        value,
        bytes.fromhex(without_0x(data)),
        operation,
        nonce,
        deadline,
    )
    return await contract_instance.functions.getMessageHash(*params).call()
