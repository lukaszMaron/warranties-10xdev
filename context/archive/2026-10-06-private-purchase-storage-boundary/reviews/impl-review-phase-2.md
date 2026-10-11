<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Private Profile Storage and Recovery Implementation Plan

- **Plan**: context/changes/private-purchase-storage-boundary/plan.md
- **Scope**: Phase 2 of 2
- **Reviewed phases**: 2
- **Date**: 2026-10-11
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical, 2 warnings, 3 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

## Findings

### F1 — Retention downloads and re-validates every archive on each run

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: src/warranties_10xdev/backup.py:307
- **Detail**: `prune_old_backups()` lists every matching key, then downloads and fully checksums each archive (up to 8 per daily run) before deciding what to delete. Each archive contains the database and all PDFs; at the plan's envelope (1,000 purchases, PDFs up to 20 MB) a daily run can transfer roughly 8× the profile size just for retention. The plan asks to stream data and keep backup work bounded; this cost grows linearly with profile size and is paid even when nothing is pruned.
- **Fix A ⭐ Recommended**: Validate lazily newest-first and stop once seven valid archives are confirmed; skip all downloads when there are seven or fewer matching keys.
  - Strength: Keeps the plan's "seven newest valid" semantics and the existing invalid-archive test; removes work in the common steady state.
  - Tradeoff: Still downloads up to seven archives whenever pruning is needed.
  - Confidence: HIGH — change is local to `prune_old_backups()`.
  - Blind spot: Not measured on a realistic profile size.
- **Fix B**: Trust key names for retention (archives are created and checksummed locally before upload) and leave deep validation to periodic restore drills.
  - Strength: Zero downloads during backup; simplest and fastest.
  - Tradeoff: A corrupted remote object could count toward the seven, weakening the "valid" guarantee in the plan.
  - Confidence: MED — depends on trusting the object store's integrity.
  - Blind spot: Would require updating the plan contract and the retention test.
- **Decision**: FIXED (Fix A)

### F2 — Loopback HTTP endpoint exception is not in the plan

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: src/warranties_10xdev/backup.py:107
- **Detail**: Phase 2 requires the remote destination to use TLS. Uncommitted edits now accept `http://` for `localhost`/loopback to enable local Moto smoke tests. Remote endpoints still require HTTPS and the runbook documents the exception, but the plan (the review source of truth) does not.
- **Fix**: Add a short plan addendum under Phase 2 recording the dev-only loopback HTTP exception.
- **Decision**: FIXED (Fix now)

### F3 — Phase 2 landed in a mixed commit with tracked cache artifacts

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: N/A (commit 6a46fdd "m2l2")
- **Detail**: Phase 2 code was committed together with unrelated S-01/frontend work (`api.py`, `pdf_extraction.py`, `frontend/`) under a non-descriptive message, unlike Phase 1's scoped `fix(private-purchase-storage-boundary): ... (p1)` commit. The same commit tracks `.pytest_cache/` and `src/warranties_10xdev/__pycache__/__init__.cpython-311.pyc`; `.pytest_cache/` is not ignored. Progress rows 2.1/2.2 have no SHA (valid while 2.3 is pending).
- **Fix**: Commit the pending Phase 2 edits as a scoped commit, untrack the cache files, and add `.pytest_cache/` and `__pycache__/` to `.gitignore`.
- **Decision**: FIXED (Fix now — .gitignore updated, caches untracked; scoped commit left to user)

### F4 — Restore accepts any key in the bucket, not only the configured prefix

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: src/warranties_10xdev/backup.py:476
- **Detail**: `_parse_backup_reference()` checks the bucket but not `WARRANTIES_BACKUP_PREFIX`, nor the `profile-<timestamp>-<id>.zip` key pattern used for retention. Archive validation still protects the target, so risk is limited to restoring an unintended object from the same private bucket.
- **Fix**: Reject keys for which `_key_timestamp(key, settings.prefix)` returns `None`.
- **Decision**: FIXED (Fix now)

### F5 — Invalid remote archives are skipped silently during retention

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: src/warranties_10xdev/backup.py:348
- **Detail**: Archives failing validation are skipped with `continue` and no output. The backup still exits 0, so an operator would not learn that stored recovery points are corrupt until a restore attempt.
- **Fix**: Print a warning to stderr listing skipped invalid keys (keep exit code 0).
- **Decision**: FIXED (Fix now)

## Verification

- `uv run pytest tests/test_backup_restore.py` — PASS (11 passed).
- `uv run pytest` — PASS (50 passed).
- Manual 2.3 — pending (unchecked). A local Moto round trip (backup → restore → SQLite marker and PDF SHA-256 match) succeeded on 2026-10-11, but it does not cover a private remote destination or a daily host schedule.

## Rejected agent claims

- Symlink escape on restore: `_validate_zip_file()` rejects any non-regular entry type and `zipfile.open` never creates links.
- Cross-volume `os.replace`: staging is created in `root.parent`, so swap stays on one volume.
- `except Exception` in `cli.py` is not dead code; it maps `botocore` `ClientError` to exit code 1.
