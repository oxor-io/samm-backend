import asyncio
import json
import os

from models import ApprovalData
from models import ProofStruct
from logger import logger

current_file_path = os.path.dirname(__file__)
GENERATE_WITNESS_FILENAME = os.path.join(current_file_path, 'scripts/generateWitness.js')
PROVER_JSON_FILENAME = os.path.join(current_file_path, 'target/prover.json')
SAMM_1024_JSON_FILENAME = os.path.join(current_file_path, 'target/samm_1024.json')
SAMM_2048_JSON_FILENAME = os.path.join(current_file_path, 'target/samm_2048.json')
WITNESS_GZ_FILENAME = os.path.join(current_file_path, 'target/witness.gz')


async def generate_zk_proof(approval_data: ApprovalData) -> ProofStruct | None:
    logger.info('Proof generation started')

    match approval_data.key_size:
        case 2048:
            is_2048_sig = True
        case 1024:
            is_2048_sig = False
        case _:
            logger.error(f'Unknown key_size: {approval_data.key_size}')
            return None

    try:
        _write_prover_json(approval_data)
        await _generate_witness_gz(is_2048_sig)
        commit, pubkey_hash, proof = await _generate_proof(is_2048_sig)
    except:
        logger.exception('Proof generation is failed')
        return None

    if not commit or not pubkey_hash or not proof:
        logger.exception(f'Proof is wrong: commit={commit} pubkey_hash={pubkey_hash} proof={proof}')
        return None

    logger.info(f'Proof is generated: commit={commit}')
    return ProofStruct(
        proof=proof.encode(),
        commit=int(commit, 16),
        domain=approval_data.domain,
        pubkeyHash=int(pubkey_hash, 16).to_bytes(length=32),
        is2048sig=is_2048_sig,
    )


def _write_prover_json(approval_data: ApprovalData):
    prover_data = {
        "root": approval_data.root,
        "path_elements": approval_data.path_elements,
        "path_indices": approval_data.path_indices,
        "signature": approval_data.signature,
        "padded_member": approval_data.padded_member,
        "secret": approval_data.secret,
        "relayer_address": approval_data.relayer_address,
        "msg_hash": approval_data.msg_hash,
        "header": {"len": approval_data.header_length, "storage": approval_data.header},
        "relayer": {"len": approval_data.padded_relayer_length, "storage": approval_data.padded_relayer},
        "domain": {"len": approval_data.padded_domain_length, "storage": approval_data.padded_domain},
        "pubkey": {"modulus": approval_data.pubkey_modulus_limbs, "redc": approval_data.redc_params_limbs},
        "from_seq": {"index": approval_data.from_seq.index, "length": approval_data.from_seq.length},
        "member_seq": {"index": approval_data.member_seq.index, "length": approval_data.member_seq.length},
        "to_seq": {"index": approval_data.to_seq.index, "length": approval_data.to_seq.length},
        "relayer_seq": {"index": approval_data.relayer_seq.index, "length": approval_data.relayer_seq.length}
    }
    logger.info(f'Prover data: {prover_data}')

    # Serializing json
    json_object = json.dumps(prover_data, indent=4)

    # write to prover file
    with open(PROVER_JSON_FILENAME, 'w+') as file:
        file.write(json_object)


async def _generate_witness_gz(is_2048_sig: bool):
    # node scripts/generateWitness.js
    logger.info('Generating witness... ⌛')
    process = await asyncio.create_subprocess_exec(
        'node',
        GENERATE_WITNESS_FILENAME,
        str(is_2048_sig),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    logger.info(f'subprocess: {process}')
    (stdout, stderr) = await process.communicate()
    if stderr:
        logger.error(f'Witness generation is failed ⭕: {stderr}')
        raise

    logger.info(f'Witness is generated ✅: {stdout}')


async def _generate_proof(is_2048_sig: bool) -> tuple[str, str, str]:
    logger.info('Generating proof... ⌛')
    # bb prove_ultra_keccak_honk -b ./target/samm_2048.json -w ./target/witness.gz -o -
    process = await asyncio.create_subprocess_exec(
        'bb',
        'prove_ultra_keccak_honk',
        '-b',
        SAMM_2048_JSON_FILENAME if is_2048_sig else SAMM_1024_JSON_FILENAME,
        '-w',
        WITNESS_GZ_FILENAME,
        '-o',
        '-',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    logger.info(f'subprocess: {process}')
    (stdout, stderr) = await process.communicate()
    if stderr:
        logger.error(f'Proof generation is failed ⭕: {stderr}')
        raise

    logger.info('Proof is generated ✅')

    # https://github.com/oxor-io/samm-circuits?tab=readme-ov-file#prepare-proof-for-smart-contract-tests
    # split to public inputs, outputs (commit, pubkeyHash) and proof itself
    # first output
    shift = 4
    commit = stdout[(shift+6368):((shift+6368) + 32)].hex()
    # second output
    pubkey_hash = stdout[(shift+6368+32):((shift+6368+32) + 32)].hex()
    # proof
    proof = stdout[shift:shift+96].hex() + stdout[shift+6432:].hex()

    return commit, pubkey_hash, proof
