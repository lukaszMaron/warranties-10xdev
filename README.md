# warranties-10xdev
Course repo with warranties project

## Agent quality hooks

Copilot hooks are configured in [quality.json](.github/hooks/quality.json);
[quality.mjs](.github/hooks/quality.mjs) requires Node, Git and the project's
Python environment (`uv sync --locked`). Install frontend dependencies with
`npm ci` from `frontend/`.

- After an edit: Python/JavaScript syntax checks on the edited files only.
  For frontend TypeScript/TSX, Astro sync + TypeScript diagnostics are filtered
  to those files. There is no linter, Python typechecker, JSX parser or Astro
  template checker yet; files outside those configured scopes are skipped.
- Risk #1 (PDF import/correction): editing
  `src/warranties_10xdev/pdf_extraction.py` also runs only
  `tests/test_pdf_extraction.py`, `tests/test_pdf_preview_api.py` and
  `tests/test_pdf_purchase_flow.py` with `python -m pytest -q`.
  These directly import the extraction module and cover extraction, preview
  and preserving manual corrections. Editing one of those test files runs
  only that test file; other modules do not trigger this suite. Multi-file
  edits deduplicate the selected tests. Successful runs report the test paths
  and pytest result in `additionalContext`, so execution is observable.
  Failures use the same feedback channel; CLI post-edit hooks cannot hard-block
  a turn. The end-of-turn hook remains the blocking safety net.
  This is the backend portion of risk #1, not proof of browser form state.
- Before finishing: syntax checks on changed and untracked files, related
  application pytest tests, then `astro sync` + `tsc --noEmit --pretty false`
  in `frontend/`.
  This also catches shell-written edits. A blocked turn gets one retry;
  `stop_hook_active` prevents a loop.
  The expensive hook/Git proof suites run explicitly or in full pytest/CI,
  not in every agent turn. This scope was approved after the complete suite
  exceeded the hook's 120-second budget.
- Paths resolve from the payload checkout, including sibling worktrees of the
  same repository. Session checkout registrations live in the OS temporary
  directory; they contain paths only and can be removed after the session.
  Do not run parallel editing sessions against the same checkout.

Static checks were explicitly enabled ahead of Phase 4 of the
[test plan](context/foundation/test-plan.md). Browser e2e, production builds,
new linters and git hooks are not added by this setup. Passing these hooks
does not prove PDF upload/correction/save behavior in the browser, hydration,
or database/file recovery; those still need integration and browser verification.

Run the persistent hook proof with
`uv run pytest tests/agent-hooks.test.py -q`, or run `uv run pytest -q` to
include it in the existing suite and CI gate. The proof uses temporary Git
repositories, real Python/JavaScript syntax checks and pytest, and simulated
Astro/TypeScript tools to verify feedback contracts without installing packages.
The related-PDF proof uses real pytest assertions and also verifies that a
non-PDF edit starts no tests, editing a test starts only that file, missing tests
fail visibly, and multi-file edits do not run a test twice.

### Manual related-test check (PowerShell)

From the checkout root, pipe an edit payload into the real script:

```powershell
@{
  cwd = (Get-Location).Path
  toolName = 'edit'
  toolArgs = @{ path = 'src\warranties_10xdev\pdf_extraction.py' }
} | ConvertTo-Json -Depth 4 -Compress | node '.github\hooks\quality.mjs' edit
```

Expect exit 0 and a JSON `additionalContext` naming only the three PDF test
files and their result. In an isolated copy, deliberately change an expected
value in one PDF test to make an assertion fail: the same payload must report
`Quality checks failed`, the failing test and `AssertionError`. Restore the
assertion and expect a passing summary. A payload pointing to `README.md` must
produce no PDF-test output, even while that unrelated PDF assertion is failing.
With Local event payloads, read `hookSpecificOutput.additionalContext` instead.
Manual stdin checks prove the script, not automatic host dispatch: confirm
dispatch separately in the hooks/debug log after a real agent edit.

Trust the workspace and restart the Copilot session to load the hooks. In VS
Code Local, ensure `chat.useHooks` is enabled; inspect the agent debug log for
`PostToolUse`/`Stop` executions. In the Copilot CLI/Agent Host runtime, inspect
the hooks/debug log for `postToolUse`/`agentStop`. The scripts select the
appropriate output shape from the payload; do not duplicate registration in
Claude settings. An actual agent-triggered failure is still needed to confirm
that the selected runtime delivers the feedback to the model.

## Git pre-commit gate

The Git gate is separate from Copilot hooks. It uses
[pre-commit configuration](.pre-commit-config.yaml), Ruff for Python, and ESLint
with TypeScript/Astro support for the frontend. No formatter or auto-fix runs.

Install once per checkout (Node 22.13+ or a supported newer Node is required):

```powershell
uv sync --locked
npm --prefix frontend ci
uv run --locked pre-commit install
```

Then `git commit` automatically checks:

- Ruff on staged Python files under `src/`, `tests/`, and `scripts/`.
- ESLint on staged frontend source files (`.astro`, JS and TS variants) and
  Astro/ESLint configuration. CSS has no linter in this gate.
- pytest files importing staged backend modules, including transitive
  dependencies; staged test files run themselves. Editing the selector or
  test fixtures runs all backend tests. See
  [the selector](scripts/staged_tests.py).

The manager temporarily stashes unstaged tracked changes, checks the index
version, then restores them. It does not stage files or modify their contents.
As usual, untracked files are not stashed; do not rely on untracked modules to
make staged tests pass. Deleted paths are not sent to these hooks by pre-commit;
run the full suite after deletions and dependency/configuration changes.
The Python launcher uses this checkout's `.venv`, not a global interpreter.
Missing dependencies or failing assertions block the commit with a nonzero exit.

Run on the current index with `uv run --locked pre-commit run`. To check named
working-tree files explicitly:

```powershell
uv run --locked pre-commit run --files src/warranties_10xdev/pdf_extraction.py frontend/src/lib/api.ts
```

Stage the gate configuration and its dependencies before using it in a real
commit; pre-commit refuses an unstaged configuration. Hook installation is local
and must be repeated by other contributors. To remove the local installation:
`uv run --locked pre-commit uninstall`.

Proof: `uv run --locked pytest tests/test_staged_tests.py -q` tests staged-only
lint and assertions, partial-staging restoration, frontend lint, and blocked
and successful Git commits in temporary repositories. It uses installed tools;
run both dependency-install commands first. No commits are made in this project.
The pytest fixture in [conftest.py](tests/conftest.py) removes repository-local
Git environment variables from each test, so temporary repositories cannot
inherit the parent commit's index or worktree. Regression cases also run the
worktree/commit proofs with deliberately contaminated parent environments.

There is no frontend application-test runner yet. Frontend lint is not a
behavioral test and cannot prove hydration or purchase submission. This gate
does not run builds, typechecks, browser tests or cloud-dependent checks.
The existing agent end-of-turn checks remain separate.

Recommended (not configured): full pytest and frontend production build before
push. Keep browser e2e and manual restore checks at their planned rollout gates.
