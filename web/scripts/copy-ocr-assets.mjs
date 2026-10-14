import { copyFile, mkdir, readdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const target = resolve(root, "public/vendor/tesseract");
await mkdir(target, { recursive: true });
await copyFile(resolve(root, "node_modules/tesseract.js/dist/worker.min.js"), resolve(target, "worker.min.js"));
const core = resolve(root, "node_modules/tesseract.js-core");
for (const name of await readdir(core)) {
  if (/^tesseract-core.*\.(js|wasm)$/.test(name)) await copyFile(resolve(core, name), resolve(target, name));
}
console.log("Local OCR worker and WebAssembly assets prepared.");
