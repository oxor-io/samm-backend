import samm_2048 from '../target/samm_2048.json' with { type: "json" };
import input from '../target/prover.json' with { type: "json" };
// import { UltraHonkBackend } from '@noir-lang/backend_barretenberg';
import { Noir } from '@noir-lang/noir_js';
import fs from 'fs';


async function main() {
    // const backend = new UltraHonkBackend(samm_2048);
    const noir = new Noir(samm_2048);

    const { witness } = await noir.execute(input);
    // const proof = await backend.generateProof(witness);

    fs.writeFileSync('./target/witness.gz', witness, (err) => {
        if (err) throw err;
        console.log('File has been saved!');
    });

    // console.log('logs', 'Verifying proof... ⌛');
    // const isValid = await backend.verifyProof(proof);
    // if (isValid) console.log('logs', 'Verifying proof... ✅');
}
  
main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error)
        process.exit(1)
    })
