import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("staged_tests", ROOT / "scripts" / "staged_tests.py")
assert SPEC and SPEC.loader
SELECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SELECTOR)


def command(root, *args):
    return subprocess.run(args, cwd=root, text=True, capture_output=True, check=False, timeout=120)


def git(root, *args):
    result = command(root, "git", *args)
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.fixture
def repository(tmp_path):
    root = tmp_path / "staged proof with spaces"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "proof@example.invalid")
    git(root, "config", "user.name", "Pre-commit proof")
    source = root / "src" / "example"
    source.mkdir(parents=True)
    (source / "__init__.py").write_text("")
    (source / "core.py").write_text("VALUE = 42\n")
    (source / "service.py").write_text("from .core import VALUE\n")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_service.py").write_text(
        "import runpy\nfrom pathlib import Path\n"
        "def test_value():\n"
        "    module = Path(__file__).resolve().parents[1] / 'src/example/core.py'\n"
        "    assert runpy.run_path(str(module))['VALUE'] == 42\n"
    )
    (tests / "test_import.py").write_text(
        "from example import service\n"
        "def test_imported_value():\n"
        "    assert service.VALUE == 42\n"
    )
    scripts = root / "scripts"
    scripts.mkdir()
    shutil.copyfile(ROOT / "scripts" / "staged_tests.py", scripts / "staged_tests.py")
    (root / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n.ruff_cache/\n")
    (root / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["src"]\n'
        '[tool.ruff.lint]\nselect = ["E4", "E7", "E9", "F"]\n'
    )
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    # Keep real filtering/stashing, but use this test environment's installed tools.
    hooks = config["repos"][0]["hooks"]
    for hook in hooks:
        if hook["id"] == "ruff-staged":
            hook["entry"] = f'"{sys.executable}" -m ruff check'
        elif hook["id"] == "pytest-staged":
            hook["entry"] = f'"{sys.executable}" scripts/staged_tests.py'
        elif hook["id"] == "eslint-staged":
            eslint = ROOT / "frontend" / "node_modules" / "eslint" / "bin" / "eslint.js"
            config_path = ROOT / "frontend" / "eslint.config.mjs"
            hook["entry"] = f'node "{eslint}" --config "{config_path}" --max-warnings 0'
    (root / ".pre-commit-config.yaml").write_text(yaml.safe_dump(config))
    git(root, "add", ".")
    git(root, "commit", "-qm", "Proof baseline")
    return root


def test_selects_transitive_imports_and_direct_test(repository):
    assert SELECTOR.select_tests(repository, ["src/example/core.py"]) == ["tests/test_import.py"]
    assert SELECTOR.select_tests(repository, ["tests/test_service.py"]) == ["tests/test_service.py"]
    assert SELECTOR.select_tests(repository, ["frontend/src/lib/api.ts"]) == []
    assert SELECTOR.select_tests(repository, ["README.md"]) == []


def test_includes_relative_imports_and_deduplicates(repository):
    selected = SELECTOR.select_tests(
        repository, ["src/example/core.py", "src/example/service.py", "tests/test_import.py"],
    )
    assert selected == ["tests/test_import.py"]


def test_hook_selector_changes_run_all_tests(repository):
    assert SELECTOR.select_tests(repository, ["scripts/staged_tests.py"]) == [
        "tests/test_import.py", "tests/test_service.py",
    ]


@pytest.mark.parametrize("variable", ["GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE"])
def test_proofs_ignore_parent_commit_git_environment(tmp_path, variable):
    env = {**os.environ, variable: ".git/index" if variable == "GIT_INDEX_FILE" else str(tmp_path / "missing")}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "tests/agent-hooks.test.py::test_sibling_worktree_sweep_and_config_commands",
         "tests/test_staged_tests.py::test_installed_git_hook_blocks_bad_commit_and_allows_clean_commit"],
        cwd=ROOT, env=env, text=True, capture_output=True, check=False, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 passed" in result.stdout


def test_agent_sweep_explicitly_excludes_expensive_proof_suites(repository):
    for name in ("agent-hooks.test.py", "test_staged_tests.py"):
        (repository / "tests" / name).write_text("raise AssertionError('expensive proof must not run')\n")
    result = command(
        repository, sys.executable, "scripts/staged_tests.py", "--agent", "scripts/staged_tests.py",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 passed" in result.stdout
    assert "proof suites run explicitly" in result.stdout


def run_gate(repository):
    return command(repository, sys.executable, "-m", "pre_commit", "run", "--show-diff-on-failure")


def test_staged_lint_failure_blocks_and_restores_unstaged_fix(repository):
    file = repository / "src" / "example" / "core.py"
    file.write_text("import os\nVALUE = 42\n")
    git(repository, "add", str(file))
    file.write_text("VALUE = 42\n")
    before = git(repository, "diff", "--cached")
    result = run_gate(repository)
    assert result.returncode != 0
    assert "F401" in result.stdout + result.stderr
    assert file.read_text() == "VALUE = 42\n"
    assert git(repository, "diff", "--cached") == before


def test_staged_failing_assertion_blocks_and_restores_fix(repository):
    file = repository / "tests" / "test_service.py"
    clean = file.read_text()
    file.write_text(clean.replace("== 42", "== 43"))
    git(repository, "add", str(file))
    file.write_text(clean)
    before = git(repository, "diff", "--cached")
    result = run_gate(repository)
    assert result.returncode != 0
    assert "AssertionError" in result.stdout + result.stderr
    assert file.read_text() == clean
    assert git(repository, "diff", "--cached") == before


def test_clean_staged_file_passes_despite_unstaged_error(repository):
    file = repository / "src" / "example" / "core.py"
    file.write_text("VALUE = 42\n# staged clean change\n")
    git(repository, "add", str(file))
    file.write_text("def broken(:\n")
    result = run_gate(repository)
    assert result.returncode == 0, result.stdout + result.stderr
    assert file.read_text() == "def broken(:\n"


def test_documentation_skips_lint_and_tests(repository):
    file = repository / "README.md"
    file.write_text("Documentation only\n")
    git(repository, "add", str(file))
    result = run_gate(repository)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Skipped" in result.stdout


def test_staged_frontend_lint_failure_blocks_and_restores_fix(repository):
    file = repository / "frontend" / "src" / "sample.ts"
    file.parent.mkdir(parents=True)
    file.write_text("const unused = 42;\n")
    git(repository, "add", str(file))
    file.write_text("export const answer = 42;\n")
    result = run_gate(repository)
    assert result.returncode != 0
    assert "no-unused-vars" in result.stdout + result.stderr
    assert file.read_text() == "export const answer = 42;\n"


def test_installed_git_hook_blocks_bad_commit_and_allows_clean_commit(repository):
    install = command(repository, sys.executable, "-m", "pre_commit", "install")
    assert install.returncode == 0, install.stdout + install.stderr
    file = repository / "tests" / "test_service.py"
    clean = file.read_text()
    file.write_text(clean.replace("== 42", "== 43"))
    git(repository, "add", str(file))
    before = git(repository, "rev-parse", "HEAD")
    blocked = command(repository, "git", "commit", "-qm", "Must be blocked")
    assert blocked.returncode != 0
    assert "AssertionError" in blocked.stdout + blocked.stderr
    assert git(repository, "rev-parse", "HEAD") == before
    file.write_text(clean + "\n# Clean staged change\n")
    git(repository, "add", str(file))
    passed = command(repository, "git", "commit", "-qm", "Clean proof")
    assert passed.returncode == 0, passed.stdout + passed.stderr
    assert git(repository, "rev-parse", "HEAD") != before


def test_frontend_lint_fails_on_unused_variable_and_passes_clean(tmp_path):
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    hook = next(item for item in config["repos"][0]["hooks"] if item["id"] == "eslint-staged")
    # A temporary file beneath frontend uses the real installed lint config.
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    file = frontend / "sample.ts"
    eslint = ROOT / "frontend" / "node_modules" / "eslint" / "bin" / "eslint.js"
    assert eslint.exists(), "Run npm ci in frontend before the hook proof"
    args = ["node", str(eslint), "--config", str(ROOT / "frontend" / "eslint.config.mjs"),
            "--max-warnings", "0", str(file)]
    assert hook["language"] == "system"
    file.write_text("const unused = 42;\n")
    bad = command(tmp_path, *args)
    assert bad.returncode != 0
    assert "no-unused-vars" in bad.stdout + bad.stderr
    file.write_text("export const answer = 42;\n")
    clean = command(tmp_path, *args)
    assert clean.returncode == 0, clean.stdout + clean.stderr
