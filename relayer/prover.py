import asyncio
import json
import logging
import os

from models import ApprovalData
from models import ProofStruct

current_file_path = os.path.dirname(__file__)
GENERATE_WITNESS_FILENAME = os.path.join(current_file_path, 'scripts/generateWitness.js')
PROVER_JSON_FILENAME = os.path.join(current_file_path, 'target/prover.json')
SAMM_2048_JSON_FILENAME = os.path.join(current_file_path, 'target/samm_2048.json')
WITNESS_GZ_FILENAME = os.path.join(current_file_path, 'target/witness.gz')


async def generate_zk_proof(approval_data: ApprovalData) -> ProofStruct | None:
    match approval_data.key_size:
        case 2048:
            is_2048_sig = True
        case 1024:
            is_2048_sig = False
        case _:
            print('Unknown key_size:', approval_data.key_size)
            return None

    try:
        _write_prover_json(approval_data)
        await _generate_witness_gz()
        commit, pubkey_hash, proof = await _generate_proof()
    except:
        logging.exception('Proof generation is failed')

        # TODO: to uncomment
        # return None
        commit, pubkey_hash, proof = '0', '0', '0'

    if not commit or not pubkey_hash or not proof:
        commit, pubkey_hash, proof = '0', '0', '0'

    print(f'---- GENERTE ZK PROOF: {proof}')
    print(f'---- GENERTE ZK COMMIT: {commit}')
    print(f'---- GENERTE ZK COMMIT: {pubkey_hash}')

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
        "msg_hash": approval_data.msg_hash,
        "header": {"len": approval_data.header_length, "storage": approval_data.header},
        "relayer": {"len": approval_data.padded_relayer_length, "storage": approval_data.padded_relayer},
        "pubkey": {"modulus": approval_data.pubkey_modulus_limbs, "redc": approval_data.redc_params_limbs},
        "from_seq": {"index": approval_data.from_seq.index, "length": approval_data.from_seq.length},
        "member_seq": {"index": approval_data.member_seq.index, "length": approval_data.member_seq.length},
        "to_seq": {"index": approval_data.to_seq.index, "length": approval_data.to_seq.length},
        "relayer_seq": {"index": approval_data.relayer_seq.index, "length": approval_data.relayer_seq.length}
    }

    # Serializing json
    json_object = json.dumps(prover_data, indent=4)

    # write to prover file
    with open(PROVER_JSON_FILENAME, 'w+') as file:
        file.write(json_object)


async def _generate_witness_gz():
    # node scripts/generateWitness.js
    print('Generating witness... ⌛')
    process = await asyncio.create_subprocess_exec(
        'node',
        GENERATE_WITNESS_FILENAME,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    print(f'subprocess: {process}')
    (stdout, stderr) = await process.communicate()
    if stderr:
        print('Witness generation is failed ⭕: ', stderr)
        # TODO: error
        raise

    print('Witness is generated ✅: ', stdout)


async def _generate_proof() -> tuple[str, str, str]:
    print('Generating proof... ⌛')
    # bb prove_ultra_keccak_honk -b ./target/samm_2048.json -w ./target/witness.gz -o -
    process = await asyncio.create_subprocess_exec(
        'bb',
        'prove_ultra_keccak_honk',
        '-b',
        SAMM_2048_JSON_FILENAME,
        '-w',
        WITNESS_GZ_FILENAME,
        '-o',
        '-',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    print(f'subprocess: {process}')
    (stdout, stderr) = await process.communicate()
    if stderr:
        print('Proof generation is failed ⭕: ', stderr)
        # TODO: error
        raise

    print('Proof is generated ✅')

    # split to public inputs, outputs (commit, pubkeyHash) and proof itself
    # first output
    commit = stdout[5540:5572].hex()
    # second output
    pubkey_hash = stdout[5572:5604].hex()
    # proof
    proof = stdout[4:100].hex() + stdout[5604:].hex()

    return commit, pubkey_hash, proof
