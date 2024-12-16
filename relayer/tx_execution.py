import blockchain
import crud
from models import ProofStruct
from models import Transaction
from models import TransactionOperation
from models import TransactionStatus
from models import TxData
from logger import logger


async def check_threshold(tx: Transaction) -> tuple[bool, list[ProofStruct]]:
    logger.info('Check proofs threshold')

    if not await crud.check_threshold_is_confirmed(tx.id, tx.samm_id):
        return False, []

    proof_structs: list[ProofStruct] = []
    for approval in await crud.get_approvals(tx.id):
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


async def execute_transaction(tx: Transaction, proof_structs: list[ProofStruct]) -> TransactionStatus:
    logger.info(f'Execute transaction id={tx.id}')
    try:
        tx_data = TxData(
            to=tx.to,
            value=tx.value,
            data=tx.data,
            operation=TransactionOperation(tx.operation),
            nonce=tx.nonce,
            deadline=tx.deadline,
        )
        success, tx_receipt = await blockchain.execute_transaction(tx.samm.samm_address, tx_data, proof_structs)
    except:
        logger.exception('Unknow exception during blockchain communication.')
    else:
        match (success, tx_receipt):
            case False, None:
                logger.error('Contract reverts error')
                return TransactionStatus.failed
            case False, _:
                logger.error('Contract returns "false"')
                return TransactionStatus.failed
            case True, None:
                logger.warning('Transaction was sent, but timeout was reached')
                return TransactionStatus.sent
            case True, _:
                return TransactionStatus.success

    return TransactionStatus.failed


async def change_transaction_status(tx: Transaction, status: TransactionStatus):
    logger.info(f'New status: {status}')
    await crud.change_transaction_status(tx.id, status)

