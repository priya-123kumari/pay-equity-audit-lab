// Copies the generated dataset into public/data so the dev server can serve it.
// Default source: ../data/full   Override:  DATA_DIR=/absolute/path/to/data/starter npm run dev
import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(process.env.DATA_DIR ?? resolve(here, "../../data/full"));
const dst = resolve(here, "../public/data");

if (!existsSync(src)) {
  console.error(`Data folder not found: ${src}\nGenerate it first (from the repo root):\n  python -m generator --seed 20261022 --employees 5000 --out data/full`);
  process.exit(1);
}
rmSync(dst, { recursive: true, force: true });
mkdirSync(dst, { recursive: true });
for (const p of ["json", "ground_truth", "outputs", "manifest", "checksums.json"]) {
  cpSync(resolve(src, p), resolve(dst, p), { recursive: true });
}
console.log(`Data synced from ${src}`);
