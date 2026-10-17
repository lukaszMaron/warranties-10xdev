import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";

const mode = process.argv[2];
const environment = { ...process.env, NO_COLOR: "1", FORCE_COLOR: "0" };
const deadline = Date.now() + (mode === "stop" ? 105_000 : 25_000);
const scriptRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

function parse(value) {
  try {
    return JSON.parse(value);
  } catch (error) {
    if (error instanceof SyntaxError) return {};
    throw error;
  }
}

function run(command, args, cwd) {
  const remaining = deadline - Date.now();
  if (remaining <= 0) throw new Error("Quality hook exceeded its check budget.");
  const result = spawnSync(command, args, {
    cwd,
    env: environment,
    encoding: "utf8",
    timeout: Math.min(remaining, mode === "stop" ? 90_000 : 25_000),
    maxBuffer: 2 * 1024 * 1024,
    windowsHide: true,
  });
  if (result.error) throw new Error(`${command}: ${result.error.message}`);
  const output = `${result.stdout || ""}${result.stderr || ""}`;
  return { ok: result.status === 0, output: output || (result.status === 0 ? "" : `${command} exited ${result.status}`) };
}

function git(cwd, args) {
  const result = run("git", args, cwd);
  if (!result.ok) throw new Error(result.output);
  return result.output;
}

function rootAt(cwd) {
  return git(cwd, ["rev-parse", "--show-toplevel"]).trim();
}

function commonAt(root) {
  return fs.realpathSync(git(root, ["rev-parse", "--path-format=absolute", "--git-common-dir"]).trim());
}

function python(root) {
  const local = path.join(root, ".venv", process.platform === "win32" ? "Scripts" : "bin",
    process.platform === "win32" ? "python.exe" : "python");
  return fs.existsSync(local) ? local : "python";
}

function pathsIn(value, found = new Set()) {
  if (!value || typeof value !== "object") return found;
  for (const [key, item] of Object.entries(value)) {
    if (["file_path", "filePath", "path"].includes(key) && typeof item === "string") found.add(item);
    else if (item && typeof item === "object") pathsIn(item, found);
  }
  return found;
}

function patchPaths(patch) {
  if (typeof patch !== "string") return [];
  return [...patch.matchAll(/^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$/gm)]
    .map((match) => match[1].trim());
}

function covered(file, root) {
  if (/\.(?:py|[cm]?js)$/i.test(file)) return true;
  return /\.tsx?$/i.test(file) &&
    path.relative(root, file).startsWith(`frontend${path.sep}`);
}

function typecheck(root) {
  const frontend = path.join(root, "frontend");
  const astro = path.join(frontend, "node_modules", "astro", "bin", "astro.mjs");
  const tsc = path.join(frontend, "node_modules", "typescript", "bin", "tsc");
  for (const tool of [astro, tsc]) {
    if (!fs.existsSync(tool)) throw new Error(`Missing ${tool}; run npm ci in frontend.`);
  }
  const sync = run(process.execPath, [astro, "sync"], frontend);
  if (!sync.ok) throw new Error(`Astro sync failed:\n${sync.output}`);
  return run(process.execPath, [tsc, "--project", "tsconfig.json", "--noEmit", "--pretty", "false"], frontend);
}

function checkFiles(root, files) {
  const errors = [];
  for (const file of files) {
    if (!covered(file, root) || !fs.existsSync(file) || !fs.statSync(file).isFile()) continue;
    let result;
    if (/\.py$/i.test(file)) {
      result = run(python(root), ["-c",
        "import ast,sys,tokenize; p=sys.argv[1]; f=tokenize.open(p); s=f.read(); f.close(); ast.parse(s,filename=p)",
        file], root);
    } else if (/\.(?:[cm]?js)$/i.test(file)) {
      result = run(process.execPath, ["--check", file], root);
    }
    if (result && !result.ok) errors.push(`${file}:\n${result.output}`);
  }
  return errors;
}

function relatedPdfTests(root, files) {
  const tests = [
    "tests/test_pdf_extraction.py",
    "tests/test_pdf_preview_api.py",
    "tests/test_pdf_purchase_flow.py",
  ];
  const selected = new Set();
  for (const file of files) {
    const relative = path.relative(root, file).replaceAll("\\", "/");
    if (relative === "src/warranties_10xdev/pdf_extraction.py") {
      for (const test of tests) selected.add(test);
    } else if (tests.includes(relative)) {
      selected.add(relative);
    }
  }
  if (!selected.size) return null;
  const paths = [...selected];
  const result = run(python(root), ["-m", "pytest", "-q", ...paths], root);
  return { ...result, output: `Related PDF tests (${paths.join(", ")}):\n${result.output}` };
}

function emit(payload, message, failed = true) {
  if (!message) return;
  const text = (failed ? `Quality checks failed. Fix these before finishing:\n${message}` : message).slice(0, 9000);
  const local = typeof payload.hook_event_name === "string";
  const specific = mode === "stop"
    ? { hookEventName: "Stop", decision: "block", reason: text }
    : { hookEventName: "PostToolUse", additionalContext: text };
  console.log(JSON.stringify(local ? { hookSpecificOutput: specific }
    : mode === "stop" ? { decision: "block", reason: text } : { additionalContext: text }));
}

function main(payload) {
  if (mode === "stop" && payload.stop_hook_active === true) return;
  if (!["edit", "stop"].includes(mode)) throw new Error(`Unknown hook mode: ${mode}`);
  if (typeof payload.cwd !== "string" || !payload.cwd) return;
  const cwd = path.resolve(payload.cwd);
  const root = rootAt(cwd);
  const common = commonAt(root);
  if (common !== commonAt(scriptRoot)) return;
  const session = payload.sessionId ?? payload.session_id;
  const registry = typeof session === "string" && session
    ? path.join(os.tmpdir(), `warranties-hooks-${createHash("sha256").update(`${common}\0${session}`).digest("hex")}.json`)
    : null;
  const roots = new Set([root]);
  if (registry && fs.existsSync(registry)) {
    const saved = JSON.parse(fs.readFileSync(registry, "utf8"));
    if (!Array.isArray(saved) || saved.some((item) => typeof item !== "string")) {
      throw new Error("Invalid quality hook checkout registry.");
    }
    for (const item of saved) {
      if (commonAt(item) === common) roots.add(item);
    }
  }
  const errors = [];
  const passedTests = [];
  if (mode === "edit") {
    const tool = payload.toolName ?? payload.tool_name ?? "";
    if (typeof tool !== "string" || /read|view|search|grep|list|glob|fetch|get_/i.test(tool)) return;
    let args = payload.tool_input ?? payload.toolArgs ?? {};
    const rawArgs = args;
    if (typeof args === "string") args = parse(args);
    const paths = pathsIn(args);
    const patch = typeof rawArgs === "string" && rawArgs.startsWith("*** Begin Patch")
      ? rawArgs : args?.input ?? args?.patch;
    for (const file of patchPaths(patch)) paths.add(file);
    const groups = new Map();
    for (const file of paths) {
      const absolute = path.resolve(cwd, file);
      if (!fs.existsSync(absolute) || !fs.statSync(absolute).isFile()) continue;
      const checkout = rootAt(path.dirname(absolute));
      if (commonAt(checkout) !== common || !covered(absolute, checkout)) continue;
      roots.add(checkout);
      if (!groups.has(checkout)) groups.set(checkout, []);
      groups.get(checkout).push(absolute);
    }
    if (registry && groups.size) fs.writeFileSync(registry, JSON.stringify([...roots]), { mode: 0o600 });
    for (const [checkout, files] of groups) {
      errors.push(...checkFiles(checkout, files));
      const related = relatedPdfTests(checkout, files);
      if (related) {
        if (related.ok) passedTests.push(related.output);
        else errors.push(related.output);
      }
      if (files.some((file) => /\.tsx?$/i.test(file))) {
        const result = typecheck(checkout);
        if (!result.ok) {
          const relative = files.map((file) => path.relative(path.join(checkout, "frontend"), file).replaceAll("\\", "/"));
          const lines = result.output.split(/\r?\n/).filter((line) =>
            relative.some((file) => line.replaceAll("\\", "/").startsWith(`${file}(`)));
          if (lines.length) errors.push(lines.join("\n"));
          else if (!/\(\d+,\d+\): error TS\d+/.test(result.output)) errors.push(result.output);
        }
      }
    }
  } else {
    for (const checkout of roots) {
      const tracked = git(checkout, ["diff", "--name-only", "-z", "HEAD", "--"]);
      const untracked = git(checkout, ["ls-files", "--others", "--exclude-standard", "-z"]);
      const names = [tracked, untracked].flatMap((value) => value.split("\0").filter(Boolean));
      if (!names.length) continue;
      const files = [...new Set(names)].map((file) => path.resolve(checkout, file));
      errors.push(...checkFiles(checkout, files));
      for (const [name, check] of [
        ["pytest", () => run(python(checkout), [
          path.join(checkout, "scripts", "staged_tests.py"), "--agent", ...names,
        ], checkout)],
        ["TypeScript", () => typecheck(checkout)],
      ]) {
        try {
          const result = check();
          if (!result.ok) errors.push(`${checkout} ${name}:\n${result.output}`);
        } catch (error) {
          errors.push(`${checkout} ${name}: ${error.message}`);
        }
      }
    }
  }
  emit(payload, errors.join("\n\n"));
  if (!errors.length && passedTests.length) emit(payload, passedTests.join("\n\n"), false);
}

const input = parse(fs.readFileSync(0, "utf8"));
const payload = input && typeof input === "object" && !Array.isArray(input) ? input : {};
try {
  main(payload);
} catch (error) {
  emit(payload, error instanceof Error ? error.message : String(error));
}
