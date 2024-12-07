import json

from models import ApprovalData
from models import ProofStruct


async def generate_zk_proof(approval_data: ApprovalData) -> ProofStruct:
    proverData = {
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
    json_object = json.dumps(proverData, indent=4)

    # write to prover file
    with open('./target/prover.json', 'w+') as file:
        file.write(json_object)

    # node scripts/generateWitness.js
    print('Generating witness... ⌛')
    process = await asyncio.create_subprocess_exec('node', 'scripts/generateWitness.js')
    print(f'subprocess: {process}')
    await process.wait()
    print('Generating witness... ✅')

    print('Generating proof... ⌛')
    # bb prove_ultra_keccak_honk -b ./target/samm_2048.json -w ./target/witness.gz -o ./target/proof
    process = await asyncio.create_subprocess_exec('bb', 'prove_ultra_keccak_honk', '-b', './target/samm_2048.json', '-w', './target/witness.gz', '-o', './target/proof')
    print(f'subprocess: {process}')
    await process.wait()
    print('Generating proof... ✅')

    # read proof and split to public inputs, outputs (commit, pubkeyHash) and proof itself
    data = b''
    with open('./target/proof', 'rb') as file:
        data = file.read()

    # first output
    commit = data[5540:5572].hex()
    # second output
    pubkeyHash = data[5572:5604].hex()
    # proof
    proof = data[4:100].hex() + data[5604:].hex()

    match approval_data.key_size:
        case 2048:
            is_2048_sig = True
        case 1024:
            is_2048_sig = False
        case _:
            # TODO: error
            raise

    print(f'---- GENERTE ZK PROOF: {proof}')
    print(f'---- GENERTE ZK COMMIT: {commit}')
    print(f'---- GENERTE ZK COMMIT: {pubkeyHash}')
    return ProofStruct(
        proof=proof.encode(),
        commit=int(commit, 16),
        domain=approval_data.domain,
        pubkeyHash=int(pubkeyHash, 16).to_bytes(length=32),
        is2048sig=is_2048_sig,
    )
