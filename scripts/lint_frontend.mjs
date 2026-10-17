import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const frontend = path.join(root, "frontend");
const files = process.argv.slice(2).map((file) => path.resolve(root, file));
if (files.length) {
  // Astro's virtual script paths must resolve from the frontend config directory.
  const result = spawnSync(process.execPath, [
    path.join(frontend, "node_modules", "eslint", "bin", "eslint.js"),
    "--config", path.join(frontend, "eslint.config.mjs"), "--max-warnings", "0", ...files,
  ], {
    cwd: frontend,
    stdio: "inherit",
    env: { ...process.env, NO_COLOR: "1", FORCE_COLOR: "0" },
  });
  if (result.error) console.error(`Cannot run frontend lint: ${result.error.message}`);
  process.exitCode = result.status ?? 1;
}
