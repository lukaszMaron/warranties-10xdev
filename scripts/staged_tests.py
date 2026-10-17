"""Select pytest files importing staged modules, including transitive imports."""

import ast
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def imports(file: Path, module: str) -> set[str]:
    tree = ast.parse(file.read_text(encoding="utf-8-sig"), filename=str(file))
    dependencies: set[str] = set()
    package = module if file.name == "__init__.py" else module.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            dependencies.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix = node.module or ""
            if node.level:
                parts = package.split(".")
                prefix = ".".join(parts[:len(parts) - node.level + 1] + ([prefix] if prefix else []))
            dependencies.add(prefix)
            dependencies.update(f"{prefix}.{alias.name}" for alias in node.names)
    return dependencies


def select_tests(root: Path, changed: list[str]) -> list[str]:
    paths = {Path(name).as_posix() for name in changed}
    tests = sorted((root / "tests").glob("*.py"))
    selected = {name for name in paths if name.startswith("tests/") and (root / name).is_file()}
    if any(name in {"scripts/staged_tests.py", "tests/conftest.py"} for name in paths):
        return [file.relative_to(root).as_posix() for file in tests]
    modules = {}
    for file in (root / "src").rglob("*.py"):
        relative = file.relative_to(root / "src").with_suffix("")
        module = ".".join(relative.parts)
        if file.name == "__init__.py":
            module = module.removesuffix(".__init__")
        modules[module] = file
    affected = {module for module, file in modules.items() if file.relative_to(root).as_posix() in paths}
    dependencies = {module: imports(file, module) for module, file in modules.items()}
    while True:
        dependents = {
            module for module, deps in dependencies.items()
            if any(dep == item or dep.startswith(item + ".") for dep in deps for item in affected)
        }
        expanded = affected | dependents
        if expanded == affected:
            break
        affected = expanded
    for file in tests:
        deps = imports(file, "")
        if any(dep == item or dep.startswith(item + ".") for dep in deps for item in affected):
            selected.add(file.relative_to(root).as_posix())
    return sorted(selected)


def main() -> int:
    changed = sys.argv[1:]
    agent = bool(changed and changed[0] == "--agent")
    if agent:
        changed = changed[1:]
    try:
        tests = select_tests(ROOT, changed)
    except (OSError, SyntaxError, UnicodeError) as error:
        print(f"Cannot select staged tests: {error}", file=sys.stderr)
        return 1
    if agent:
        tests = [name for name in tests if name not in {
            "tests/agent-hooks.test.py", "tests/test_staged_tests.py",
        }]
        print("Agent sweep: hook/Git proof suites run explicitly or in full pytest/CI.", flush=True)
    if not tests:
        print("No related pytest files for these paths (frontend has no test runner).")
        return 0
    print("Running related tests: " + ", ".join(tests), flush=True)
    return subprocess.call([sys.executable, "-m", "pytest", "-q", *tests], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
