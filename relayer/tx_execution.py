
import blockchain
import crud
from models import ProofStruct
from models import Transaction
from models import TransactionOperation
from models import TransactionStatus
from models import TxData


async def check_threshold(tx: Transaction) -> tuple[bool, list[ProofStruct]]:
    if not await crud.check_threshold_is_confirmed(tx.id, tx.samm_id):
        return False, []

    proof_structs: list[ProofStruct] = []
    for approval in await crud.get_approvals(tx.id):
        proof_structs.append(ProofStruct(
            proof=approval.proof,
            commit=approval.commit.from_bytes(32),
            domain=approval.domain,
            pubkeyHash=approval.pubkey_hash,
            is2048sig=approval.is_2048_sig,
        ))

    if not proof_structs:
        print('Proofs list is empty')
        raise

    return True, proof_structs


async def execute_transaction(tx: Transaction, proof_structs: list[ProofStruct]) -> TransactionStatus:
    tx_data = TxData(
        to=tx.to,
        value=tx.value,
        data=tx.data,
        operation=TransactionOperation(tx.operation),
        nonce=tx.nonce,
        deadline=tx.deadline,
    )
    is_sent = await blockchain.execute_transaction(tx.samm.samm_address, tx_data, proof_structs)
    return TransactionStatus.sent if is_sent else TransactionStatus.confirmed


async def change_transaction_status(tx: Transaction, status: TransactionStatus):
    # match status:
    #     case TransactionStatus.pending:
    #         # do nothing
    #         pass
    #     case TransactionStatus.success:
    #         # TODO: change tx.status to success
    #         pass
    #     case TransactionStatus.confirmed | TransactionStatus.sent | TransactionStatus.failed:
    #         # TODO: sent - strange state of tx
    #         # TODO: change tx.status
    #         print('tx')
    #     case _:
    #         print('Incorrect status')
    #         # TODO: return?
    await crud.change_transaction_status(tx.tx_id, status)
