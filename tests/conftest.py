import subprocess

import pytest


@pytest.fixture(autouse=True)
def isolate_git_environment(monkeypatch):
    # Git hooks export repository-local state; temporary repos must not inherit it.
    result = subprocess.run(
        ["git", "rev-parse", "--local-env-vars"],
        text=True, capture_output=True, check=True, timeout=10,
    )
    for name in result.stdout.splitlines():
        monkeypatch.delenv(name, raising=False)
