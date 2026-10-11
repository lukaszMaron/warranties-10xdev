<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Private Profile Storage and Recovery Implementation Plan

- **Plan**: context/changes/private-purchase-storage-boundary/plan.md
- **Scope**: Phase 1 of 2
- **Reviewed phases**: 1
- **Date**: 2026-10-11
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical, 1 warning, 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | WARNING |

## Findings

### F1 — Windows ACL subprocesses have no timeout

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision. Fix is obvious and narrowly scoped.
- **Dimension**: Safety & Quality
- **Location**: src/warranties_10xdev/storage.py:132
- **Detail**: `_current_windows_user_sid()` and `_apply_windows_acl()` invoke `whoami.exe` and `icacls.exe` without a timeout. If a child process stalls, constructing `ProfileStorage` can block indefinitely. The existing exception handling already converts `subprocess.SubprocessError` into a storage configuration error, so `TimeoutExpired` can be handled through the current path.
- **Fix**: Add a bounded timeout to each subprocess invocation (for example, 10 seconds).
- **Decision**: FIXED (Fix now)

### F2 — Completed manual verification has no recorded evidence

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision. Fix is obvious and narrowly scoped.
- **Dimension**: Success Criteria
- **Location**: context/changes/private-purchase-storage-boundary/plan.md:194
- **Detail**: Progress marks manual item 1.3 complete, but the commit and change records contain only the checkbox and commit SHA. There is no observable evidence that the configured data root was tested across a restart or that its files were verified as owner-only. The current automated tests cover path configuration and platform permission behavior, but do not demonstrate the stated restart/manual check.
- **Fix**: Record concise evidence for the manual check, or leave item 1.3 pending until that verification is documented.
- **Decision**: SKIPPED

## Verification

- `uv run pytest tests/test_storage.py` — PASS (15 passed).
- `uv run pytest` — PASS (47 passed).
- Manual verification item 1.3 — marked complete in Progress; independent evidence not found in the reviewed change record.
