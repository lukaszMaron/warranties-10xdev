import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const python = path.join(root, ".venv", process.platform === "win32" ? "Scripts" : "bin",
  process.platform === "win32" ? "python.exe" : "python");
const mode = process.argv[2];
if (!["lint", "tests"].includes(mode)) throw new Error(`Unknown Python quality mode: ${mode}`);
const args = mode === "lint" ? ["-m", "ruff", "check", "--force-exclude"]
  : [path.join(root, "scripts", "staged_tests.py")];
const result = spawnSync(python, [...args, ...process.argv.slice(3)], {
  cwd: root,
  stdio: "inherit",
  env: { ...process.env, NO_COLOR: "1", FORCE_COLOR: "0" },
});
if (result.error) console.error(`Cannot run Python quality gate: ${result.error.message}. Run uv sync --locked.`);
process.exitCode = result.status ?? 1;
