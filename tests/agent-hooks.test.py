import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


SOURCE = Path(__file__).resolve().parents[1]


def execute(args, cwd, *, data=None, env=None):
    return subprocess.run(
        args, cwd=cwd, input=data, text=True, capture_output=True,
        timeout=115, env=env, check=False,
    )


def git(root, *args):
    result = execute(["git", *args], root)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "checkout with spaces"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "hooks@example.invalid")
    git(root, "config", "user.name", "Hook proof")
    hooks = root / ".github" / "hooks"
    hooks.mkdir(parents=True)
    for name in ("quality.json", "quality.mjs"):
        shutil.copyfile(SOURCE / ".github" / "hooks" / name, hooks / name)
    (root / ".gitignore").write_text("node_modules/\n__pycache__/\n.pytest_cache/\n")
    (root / "sample.py").write_text("answer = 42\n")
    (root / "sample.js").write_text("const answer = 42;\n")
    (root / "tests").mkdir()
    (root / "tests" / "test_behavior.py").write_text("def test_answer():\n    assert 6 * 7 == 42\n")
    (root / "scripts").mkdir()
    shutil.copyfile(SOURCE / "scripts" / "staged_tests.py", root / "scripts" / "staged_tests.py")
    frontend = root / "frontend"
    frontend.mkdir()
    (frontend / "sample.ts").write_text("const answer: number = 42;\n")
    (frontend / "tsconfig.json").write_text("{}\n")
    astro = frontend / "node_modules" / "astro" / "bin" / "astro.mjs"
    astro.parent.mkdir(parents=True)
    astro.write_text("import fs from 'node:fs'; fs.writeFileSync('.synced', 'yes');\n")
    tsc = frontend / "node_modules" / "typescript" / "bin" / "tsc"
    tsc.parent.mkdir(parents=True)
    tsc.write_text(
        "const fs = require('node:fs');\n"
        "if (!fs.existsSync('.synced')) throw Error('sync was not run');\n"
        "if (fs.readFileSync('sample.ts','utf8').includes('WRONG_TYPE')) {\n"
        " console.log('sample.ts(1,7): error TS2322: string is not assignable to number.');\n"
        " process.exit(2);\n}\n"
    )
    git(root, "add", ".")
    git(root, "commit", "-qm", "Fixture baseline")
    return root


def invoke(root, mode, payload, *, script=None):
    env = {
        **os.environ,
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
        "CLAUDE_PROJECT_DIR": str(root / "nonexistent"),
    }
    result = execute(
        ["node", str(script or root / ".github" / "hooks" / "quality.mjs"), mode],
        root, data=payload if isinstance(payload, str) else json.dumps(payload), env=env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    return json.loads(result.stdout) if result.stdout else None


def edit(root, file="sample.py", **extra):
    return {"cwd": str(root), "toolName": "edit", "toolArgs": {"path": file}, **extra}


def test_broken_and_clean_file(checkout):
    assert invoke(checkout, "edit", edit(checkout)) is None
    (checkout / "sample.py").write_text("def broken(:\n")
    feedback = invoke(checkout, "edit", edit(checkout))
    assert "sample.py" in feedback["additionalContext"]
    assert "SyntaxError" in feedback["additionalContext"]
    (checkout / "sample.js").write_text("const answer = ;\n")
    feedback = invoke(checkout, "edit", edit(checkout, "sample.js"))
    assert "SyntaxError" in feedback["additionalContext"]
    assert "sample.js" in feedback["additionalContext"]


@pytest.mark.parametrize("payload", ["", "{}", "not json", "null", "[]",
                                      '{"toolName":"edit","toolArgs":{}}'])
def test_empty_payload(checkout, payload):
    assert invoke(checkout, "edit", payload) is None
    assert invoke(checkout, "stop", payload) is None


@pytest.mark.parametrize("file", ["README.md", "missing.py", "template.astro", "component.jsx", "outside.ts"])
def test_skipped_and_nonexistent(checkout, file):
    if file != "missing.py":
        (checkout / file).write_text("Deliberately not valid code: !!!\n")
    assert invoke(checkout, "edit", edit(checkout, file)) is None


def test_read_only_and_pathless_tools(checkout):
    (checkout / "sample.py").write_text("def broken(:\n")
    assert invoke(checkout, "edit", edit(checkout, toolName="read_file")) is None
    assert invoke(checkout, "edit", {"cwd": str(checkout), "toolName": "edit"}) is None


def test_local_and_multifile_shapes(checkout):
    (checkout / "sample.py").write_text("def broken(:\n")
    payload = {
        "cwd": str(checkout), "hook_event_name": "PostToolUse", "tool_name": "replace_string_in_file",
        "tool_input": {"replacements": [{"filePath": "sample.py"}, {"file_path": "sample.js"}]},
    }
    output = invoke(checkout, "edit", payload)
    assert "sample.py" in output["hookSpecificOutput"]["additionalContext"]
    payload = edit(checkout, toolArgs=json.dumps({"file_path": "sample.py"}))
    assert "sample.py" in invoke(checkout, "edit", payload)["additionalContext"]


def test_patch_shape(checkout):
    (checkout / "sample.py").write_text("def broken(:\n")
    payload = edit(checkout, toolName="apply_patch", toolArgs={
        "input": "*** Begin Patch\n*** Update File: sample.py\n@@\n+def broken(:\n*** End Patch"
    })
    assert "sample.py" in invoke(checkout, "edit", payload)["additionalContext"]


def test_type_diagnostics(checkout):
    assert invoke(checkout, "edit", edit(checkout, "frontend/sample.ts")) is None
    (checkout / "frontend" / "sample.ts").write_text("const answer: number = 'WRONG_TYPE';\n")
    output = invoke(checkout, "edit", edit(checkout, "frontend/sample.ts"))
    assert "sample.ts" in output["additionalContext"]
    assert "TS2322" in output["additionalContext"]
    (checkout / "frontend" / "other.ts").write_text("const other: number = 42;\n")
    assert invoke(checkout, "edit", edit(checkout, "frontend/other.ts")) is None


def test_stop_bypass_retry_and_local_output(checkout):
    assert invoke(checkout, "stop", {"cwd": str(checkout)}) is None
    (checkout / "sample.py").write_text("def broken(:\n")
    output = invoke(checkout, "stop", {"cwd": str(checkout)})
    assert output["decision"] == "block"
    assert "sample.py" in output["reason"]
    payload = {"cwd": str(checkout), "hook_event_name": "Stop"}
    assert invoke(checkout, "stop", payload)["hookSpecificOutput"]["decision"] == "block"
    assert invoke(checkout, "stop", {**payload, "stop_hook_active": True}) is None


def test_untracked_file_and_behavioral_failure(checkout):
    (checkout / "new.py").write_text("def broken(:\n")
    (checkout / "tests" / "test_behavior.py").write_text("def test_answer():\n    assert 6 * 7 == 43\n")
    output = invoke(checkout, "stop", {"cwd": str(checkout)})
    assert "new.py" in output["reason"]
    assert "test_answer" in output["reason"]
    assert "failed" in output["reason"]


def test_clean_changed_tree(checkout):
    (checkout / "sample.py").write_text("answer = 43\n")
    assert invoke(checkout, "stop", {"cwd": str(checkout)}) is None
    assert (checkout / "frontend" / ".synced").exists()


def test_no_changes_runs_no_checks(checkout):
    shutil.rmtree(checkout / "frontend" / "node_modules")
    assert invoke(checkout, "stop", {"cwd": str(checkout)}) is None


def test_missing_typechecker_is_visible(checkout):
    (checkout / "sample.py").write_text("answer = 43\n")
    (checkout / "frontend" / "node_modules" / "typescript" / "bin" / "tsc").unlink()
    output = invoke(checkout, "stop", {"cwd": str(checkout)})
    assert output["decision"] == "block"
    assert "Missing" in output["reason"]
    assert "npm ci" in output["reason"]
    output = invoke(checkout, "edit", edit(checkout, "frontend/sample.ts"))
    assert "Missing" in output["additionalContext"]


@pytest.fixture
def pdf_checkout(checkout):
    module = checkout / "src" / "warranties_10xdev" / "pdf_extraction.py"
    module.parent.mkdir(parents=True)
    module.write_text("def extracted_value():\n    return 42\n")
    tests = checkout / "tests"
    tests.mkdir(exist_ok=True)
    for name in ("test_pdf_extraction.py", "test_pdf_preview_api.py", "test_pdf_purchase_flow.py"):
        (tests / name).write_text(
            "import runpy\nfrom pathlib import Path\n\n"
            "def test_pdf_contract():\n"
            "    root = Path(__file__).resolve().parents[1]\n"
            "    with (root / 'pdf-runs.log').open('a') as log:\n"
            "        log.write(Path(__file__).name + '\\n')\n"
            "    module = runpy.run_path(str(root / 'src' / 'warranties_10xdev' / 'pdf_extraction.py'))\n"
            "    assert module['extracted_value']() == 42\n"
        )
    return checkout


@pytest.mark.parametrize("local", [False, True])
def test_related_pdf_assertion_failure_and_clean_run(pdf_checkout, local):
    root = pdf_checkout
    module = root / "src" / "warranties_10xdev" / "pdf_extraction.py"
    module.write_text("def extracted_value():\n    return 43\n")
    payload = edit(root, str(module))
    if local:
        payload = {
            "cwd": str(root), "hook_event_name": "PostToolUse", "tool_name": "edit",
            "tool_input": {"file_path": str(module)},
        }
    output = invoke(root, "edit", payload)
    message = output["hookSpecificOutput"]["additionalContext"] if local else output["additionalContext"]
    assert "Quality checks failed" in message
    assert "assert 43 == 42" in message
    assert "3 failed" in message
    module.write_text("def extracted_value():\n    return 42\n")
    output = invoke(root, "edit", payload)
    message = output["hookSpecificOutput"]["additionalContext"] if local else output["additionalContext"]
    assert "3 passed" in message
    assert "Quality checks failed" not in message


def test_related_tests_do_not_run_outside_pdf_module(pdf_checkout):
    root = pdf_checkout
    (root / "src" / "warranties_10xdev" / "pdf_extraction.py").write_text(
        "def extracted_value():\n    return 43\n"
    )
    assert invoke(root, "edit", edit(root, "sample.py")) is None
    assert invoke(root, "edit", edit(root, "README.md")) is None
    assert not (root / "pdf-runs.log").exists()


def test_editing_pdf_test_runs_only_that_test(pdf_checkout):
    root = pdf_checkout
    output = invoke(root, "edit", edit(root, "tests/test_pdf_preview_api.py"))
    assert "1 passed" in output["additionalContext"]
    assert (root / "pdf-runs.log").read_text().splitlines() == ["test_pdf_preview_api.py"]


def test_pdf_multifile_edit_deduplicates_tests(pdf_checkout):
    root = pdf_checkout
    payload = edit(root, toolArgs={"replacements": [
        {"filePath": "src/warranties_10xdev/pdf_extraction.py"},
        {"filePath": "tests/test_pdf_extraction.py"},
    ]})
    output = invoke(root, "edit", payload)
    assert "3 passed" in output["additionalContext"]
    assert len((root / "pdf-runs.log").read_text().splitlines()) == 3


def test_missing_related_test_fails_visibly(pdf_checkout):
    (pdf_checkout / "tests" / "test_pdf_extraction.py").unlink()
    output = invoke(pdf_checkout, "edit", edit(
        pdf_checkout, "src/warranties_10xdev/pdf_extraction.py",
    ))
    assert "Quality checks failed" in output["additionalContext"]
    assert "not found" in output["additionalContext"]


def test_subdirectory_and_other_repository(checkout, tmp_path):
    payload = edit(checkout, "../sample.py", cwd=str(checkout / "frontend"))
    assert invoke(checkout, "edit", payload) is None
    other = tmp_path / "unrelated"
    other.mkdir()
    git(other, "init", "-q")
    (other / "broken.py").write_text("def broken(:\n")
    assert invoke(checkout, "edit", edit(checkout, str(other / "broken.py"))) is None


def test_sibling_worktree_sweep_and_config_commands(checkout, tmp_path):
    sibling = tmp_path / "sibling"
    git(checkout, "worktree", "add", "-qb", "sibling", str(sibling))
    # The simulated tools are deliberately untracked, as node_modules is in a real checkout.
    shutil.copytree(checkout / "frontend" / "node_modules", sibling / "frontend" / "node_modules")
    (sibling / "sample.py").write_text("def broken(:\n")
    session = "proof-" + checkout.name + "-" + str(os.getpid())
    payload = edit(checkout, str(sibling / "sample.py"), sessionId=session)
    try:
        assert "sample.py" in invoke(checkout, "edit", payload)["additionalContext"]
        output = invoke(checkout, "stop", {"cwd": str(checkout), "sessionId": session})
        assert str(sibling) in output["reason"]
        assert "sample.py" in output["reason"]
        (sibling / "sample.py").write_text("answer = 42\n")
        config = json.loads((sibling / ".github" / "hooks" / "quality.json").read_text())
        for event, entries in config["hooks"].items():
            for entry in entries:
                env = {
                    **os.environ,
                    "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
                    "CLAUDE_PROJECT_DIR": str(tmp_path / "missing"),
                }
                result = subprocess.run(
                    entry["command"], shell=True, cwd=sibling / "frontend", env=env,
                    input=json.dumps({"cwd": str(sibling / "frontend")}),
                    text=True, capture_output=True, timeout=120, check=False,
                )
                assert result.returncode == 0, (event, result.stderr)
                assert result.stdout == "", (event, result.stdout)
    finally:
        import hashlib
        import tempfile
        common = str(Path(git(checkout, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve())
        digest = hashlib.sha256(f"{common}\0{session}".encode()).hexdigest()
        (Path(tempfile.gettempdir()) / f"warranties-hooks-{digest}.json").unlink(missing_ok=True)
