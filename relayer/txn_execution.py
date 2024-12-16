import blockchain
import crud
from models import ProofStruct
from models import Txn
from models import TxnOperation
from models import TxnStatus
from models import TxnData
from logger import logger


async def check_threshold(txn: Txn) -> tuple[bool, list[ProofStruct]]:
    logger.info('Check proofs threshold')

    if not await crud.check_threshold_is_confirmed(txn.id, txn.samm_id):
        return False, []

    proof_structs: list[ProofStruct] = []
    for approval in await crud.get_approvals(txn.id):
        proof_structs.append(ProofStruct(
            proof=approval.proof,
            commit=int.from_bytes(approval.commit),
            domain=approval.domain,
            pubkeyHash=approval.pubkey_hash,
            is2048sig=approval.is_2048_sig,
        ))

    if not proof_structs:
        logger.error('Proofs list is empty')
        raise

    logger.info(f'Proofs number: {len(proof_structs)}')
    return True, proof_structs


async def execute_txn(txn: Txn, proof_structs: list[ProofStruct]) -> TxnStatus:
    logger.info(f'Execute transaction id={txn.id}')
    try:
        txn_data = TxnData(
            to=txn.to,
            value=txn.value,
            data=txn.data,
            operation=TxnOperation(txn.operation),
            nonce=txn.nonce,
            deadline=txn.deadline,
        )
        success, txn_receipt = await blockchain.execute_txn(txn.samm.samm_address, txn_data, proof_structs)
    except:
        logger.exception('Unknow exception during blockchain communication.')
    else:
        match (success, txn_receipt):
            case False, None:
                logger.error('Contract reverts error')
                return TxnStatus.failed
            case False, _:
                logger.error('Contract returns "false"')
                return TxnStatus.failed
            case True, None:
                logger.warning('Transaction was sent, but timeout was reached')
                return TxnStatus.sent
            case True, _:
                return TxnStatus.success

    return TxnStatus.failed


async def change_txn_status(txn: Txn, status: TxnStatus):
    logger.info(f'New status: {status}')
    await crud.change_txn_status(txn.id, status)

