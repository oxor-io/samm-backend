import path from 'path';
import { fileURLToPath } from 'url';
// import { UltraHonkBackend } from '@noir-lang/backend_barretenberg';
import { Noir } from '@noir-lang/noir_js';
import fs from 'fs';


async function readJsonFile(filePath) {
  const json = JSON.parse(
    await fs.readFileSync(filePath)
  );
  return json;
}


async function main() {
    const __dirname = path.dirname(fileURLToPath(import.meta.url));

    const samm1024JsonPath = path.join(__dirname, '..', 'target', 'samm_1024.json');
    const samm2048JsonPath = path.join(__dirname, '..', 'target', 'samm_2048.json');
    const proverJsonPath = path.join(__dirname, '..', 'target', 'prover.json');
    const witnessGzPath = path.join(__dirname, '..', 'target', 'witness.gz');

    // is_2048_sig == 'True'
    const samm = process.argv.slice(2)[0] == 'True'
      ? await readJsonFile(samm2048JsonPath)
      : await readJsonFile(samm1024JsonPath);

    const input = await readJsonFile(proverJsonPath);

    // const backend = new UltraHonkBackend(samm_2048);
    const noir = new Noir(samm);

    const { witness } = await noir.execute(input);
    // const proof = await backend.generateProof(witness);

    fs.writeFileSync(witnessGzPath, witness, (err) => {
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
