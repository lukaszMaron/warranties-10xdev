# Private Profile Storage and Recovery Implementation Plan

## Overview

Establish the minimal persistent storage boundary for the first release: one owner's purchase metadata in SQLite and PDF files in a private data directory. Add a consistent daily off-host backup and a verified restore path for host or disk loss, with up to 24 hours of data loss and seven daily recovery points.

## Current State Analysis

- `src/warranties_10xdev/__init__.py` contains only the greeting used by the existing console entry point; there is no API, database, or file-storage implementation.
- `pyproject.toml` declares FastAPI and Uvicorn, but no persistence, object-storage, or project test dependencies. The console command is `warranties-10xdev`.
- The tech-stack hand-off specifies Python, `uv`, and self-host deployment, while leaving the database and PDF storage open.
- The PRD requires purchase data and invoice contents to be visible only to the profile owner. It starts with a local profile; accounts are future scope.
- There is no project test suite or deployment workflow to extend. The existing infrastructure research warns that metadata and PDFs stored separately need a coordinated recovery path; its multi-region and background-worker assumptions are outside this MVP.

## Desired End State

The single-owner deployment stores metadata in one SQLite database and documents under one configured private data root. The storage layer persists through application restarts, accepts PDFs up to 20 MB, and does not expose document paths as public static files. The expected personal-use envelope is one profile and up to 1,000 purchases; 1,000 is a capacity target, not an application-enforced purchase cap.

A daily host-scheduled command creates a consistent backup containing the database, PDFs, and an integrity manifest, then writes it to a private S3-compatible destination. Seven daily copies are retained. A verified restore can populate a replacement host's empty data directory; the recovery point is no older than 24 hours when the daily job succeeds.

### Key Discoveries:

- The current entry point is a two-line greeting stub: `src/warranties_10xdev/__init__.py:1-2`.
- The only runtime dependencies are FastAPI and Uvicorn; the existing console-script contract is in `pyproject.toml:10-16`.
- The roadmap names F-01 as the private storage boundary that unlocks both PDF and manual purchase entry: `context/foundation/roadmap.md:66-79`.
- The PRD defines a local profile first and per-owner access as the privacy requirement: `10xdevs/context/foundation/prd.md:84-89`.
- No application persistence, test suite, or deployment workflow exists to reuse. The project therefore needs a focused storage test suite and a host-independent backup command.

## What We're NOT Doing

- Implementing purchase fields, purchase CRUD, OCR, search, warranty calculations, or the home screen. Those belong to S-01 and S-02 and later slices.
- Adding sign-in, multi-user accounts, profile sharing, or a public multi-tenant service.
- Selecting or configuring the application hosting platform, CI/CD, reminders, or a cloud vendor.
- Providing multi-region disaster recovery, client-side backup encryption, point-in-time recovery, or a numeric restore-time guarantee.
- Enforcing a 1,000-purchase product limit. It is the capacity envelope used to validate this storage choice.

## Implementation Approach

Use the standard-library SQLite driver for single-profile metadata and a private filesystem directory for PDF bytes. Require `WARRANTIES_DATA_DIR` so production data cannot silently land in the source checkout or an ephemeral default. Keep both stores beneath that root and route all reads and writes through one storage boundary. Use a cross-process lock while creating a backup so the database snapshot and document files represent one consistent point in time.

Create an archive with a manifest and SHA-256 hashes, upload it through an S3-compatible client to a private destination with encryption at rest, and retain the seven newest daily backups. The existing CLI becomes the entry point for explicit `backup` and `restore` commands; the selected self-host environment's scheduler invokes `backup` daily. Restore validates the archive before writing to an empty replacement data directory. No purchase table or field contract is introduced here.

## Critical Implementation Details

All later purchase writes must use the shared storage boundary and its cross-process lock; otherwise a backup can pair database metadata with a PDF directory from a different moment. Restore must validate archive paths and checksums in a staging directory before activating it, and a failed backup must never replace the latest known-good backup.

## Phase 1: Private Profile Storage Boundary

### Overview

Create and test the single-owner persistence root without implementing purchase workflows. Keep PDFs outside any web/static root and make the data directory explicit and persistent across restarts.

### Changes Required:

#### 1. Storage configuration and dependencies

**File**: `pyproject.toml`, `uv.lock`

**Intent**: Add `pytest` for the focused test suite and `filelock` for cross-process coordination between document writes and backup snapshots. Keep SQLite on Python's standard library.

**Contract**: `uv sync` installs the locked dependencies; `pytest` is a development dependency, `filelock` is a runtime dependency, and `sqlite3` owns the single-profile database connection. No ORM, database server, or purchase schema is added in this phase.

#### 2. Single-profile storage boundary

**File**: `src/warranties_10xdev/storage.py`

**Intent**: Define the configured owner data root and the only supported locations for the SQLite database and private PDF directory. Fail clearly when the configured directory is missing, unwritable, or resolves inside the source checkout.

**Contract**: `WARRANTIES_DATA_DIR` resolves to a persistent root containing `profile.sqlite3` and `documents/`. The boundary initializes SQLite, applies owner-only directory permissions where supported, and provides the shared lock used by subsequent purchase writes and backup snapshots. PDF input is limited to 20 MB; the 1,000-purchase figure remains a capacity target rather than a hard cap. The directory is never mounted as static content.

#### 3. Storage contract tests

**File**: `tests/test_storage.py`

**Intent**: Add focused tests for configuration failures, database persistence after reopening, private document-root behavior, and the accepted PDF size boundary.

**Contract**: Tests use isolated temporary directories and do not read or write real profile data. POSIX permission assertions are conditional on platforms that enforce POSIX mode bits.

### Success Criteria:

#### Automated Verification:

- `uv run pytest tests/test_storage.py` passes for configured paths, invalid paths, database reopen persistence, private document storage, and the 20 MB PDF boundary.
- `uv run pytest` passes the complete project test suite.

#### Manual Verification:

- Configure `WARRANTIES_DATA_DIR` outside the source checkout, restart the application process, and confirm its persistent files remain in that directory and are readable only by the owner/service account.

**Implementation Note**: After completing this phase and its automated checks, pause for manual confirmation before proceeding to Phase 2.

## Phase 2: Daily Off-Host Backup and Restore

### Overview

Add an explicit CLI workflow that snapshots metadata and PDFs together, uploads a private off-host copy daily, keeps seven daily recovery points, and restores the bundle onto a replacement host. Do not bind scheduling to a web-process lifecycle or a specific hosting provider.

### Changes Required:

#### 1. Backup bundle and restore operations

**File**: `src/warranties_10xdev/backup.py`

**Intent**: Create a consistent snapshot under the storage lock, include the database and document tree in one archive, and make restore safe to run against a replacement data root.

**Contract**: The archive includes a versioned manifest and SHA-256 hashes for each payload. Restore rejects corrupt or path-traversal archives, validates before activation, and refuses to overwrite a non-empty data root. A failed upload leaves the previous good remote backup untouched.

#### 2. CLI and object-storage configuration

**File**: `src/warranties_10xdev/__init__.py`, `src/warranties_10xdev/cli.py`, `pyproject.toml`, `uv.lock`

**Intent**: Replace the greeting-only command with explicit backup and restore operations, and add `boto3` for provider-neutral access to an S3-compatible off-host destination.

**Contract**: `warranties-10xdev backup` uploads a uniquely dated archive; `warranties-10xdev restore <backup-reference>` restores it to a configured empty data root. Bucket, endpoint, region, and credentials come from environment configuration; credentials are never committed. The remote destination must be private, use TLS, and enable destination-side encryption at rest. The command returns a non-zero exit status on failure so the host scheduler can report it.

#### 3. Retention, scheduling, and recovery runbook

**File**: `src/warranties_10xdev/backup.py`, `docs/operations/private-profile-backup-restore.md`

**Intent**: Retain seven daily backups and document how the self-host operator configures the host scheduler, checks job failures, and restores onto a replacement host.

**Contract**: The CLI prunes only backups older than the seven newest valid daily copies, after a new upload succeeds. The runbook records required environment values, daily scheduling, credential handling, restore preconditions, and the 24-hour maximum data-loss assumption. No provider-specific scheduler or CI workflow is introduced.

#### 4. Backup and restore tests

**File**: `tests/test_backup_restore.py`

**Intent**: Verify that backups preserve a matching database/document snapshot and that recovery rejects invalid data without damaging the active profile.

**Contract**: Tests cover archive manifest/hash validation, restore to a clean temporary root, traversal/corruption rejection, upload failure preserving the prior backup, and seven-copy retention. S3 interactions use a stubbed client; tests do not require cloud credentials.

### Success Criteria:

#### Automated Verification:

- `uv run pytest tests/test_backup_restore.py` passes for consistent snapshot creation, mocked upload, integrity validation, safe restore, failure handling, and seven-copy retention.
- `uv run pytest` passes the complete project test suite, including CLI argument and error-exit behavior.

#### Manual Verification:

- Configure a private S3-compatible destination and a daily host schedule; create a backup, restore it into a clean replacement data root, and verify the database and every PDF match the source snapshot.

**Implementation Note**: After completing this phase and its automated checks, pause for manual confirmation before declaring the change complete.

## Testing Strategy

### Unit Tests:

- Test data-root resolution, permission handling, PDF size validation, and SQLite persistence across close/reopen.
- Test archive manifest generation, content hashes, retention selection, and rejection of corrupt or traversal paths.
- Test CLI argument validation and non-zero failure results without real object-storage credentials.

### Integration Tests:

- Create a temporary profile containing database data and PDFs, make a backup using a stubbed S3 client, restore to a separate empty root, and compare the restored files and database contents.
- Simulate upload failure and verify the previous valid remote backup remains available.

### Manual Testing Steps:

1. Set `WARRANTIES_DATA_DIR` to an owner-controlled persistent directory and verify the application does not place profile data in the checkout.
2. Configure a private S3-compatible backup destination and a host scheduler to run the backup command daily.
3. Restore a recent backup into a clean replacement data root and verify both database metadata and PDF files; confirm the scheduler reports a failed backup rather than silently succeeding.

## Performance Considerations

The target is one profile with up to 1,000 purchases and PDFs up to 20 MB each. Stream archive and upload contents rather than loading all document bytes into memory. Backup work runs through the CLI, outside user-facing request handling. The PRD's three-second home/search target belongs to the consuming slices and is not a storage-foundation benchmark.

## Migration Notes

There is no existing application data to migrate. This phase creates only the profile database and document root; S-01 and S-02 add purchase fields and records later. Restores are versioned by the archive manifest, and unknown archive versions fail closed rather than being partially applied.

## References

- Product privacy, local-profile scope, and open scale question: `10xdevs/context/foundation/prd.md`
- F-01 outcome and downstream dependencies: `context/foundation/roadmap.md`
- Current runtime and console-script entry point: `pyproject.toml`
- Current starter implementation: `src/warranties_10xdev/__init__.py`
- Self-host stack choice and unselected database: `10xdevs/context/foundation/tech-stack.md`
- Storage/recovery risks and provider-neutrality context: `context/foundation/infrastructure.md`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Private Profile Storage Boundary

#### Automated

- [x] 1.1 `uv run pytest tests/test_storage.py` passes for configured paths, invalid paths, database reopen persistence, private document storage, and the 20 MB PDF boundary. — 2ce7e9e
- [x] 1.2 `uv run pytest` passes the complete project test suite. — 2ce7e9e

#### Manual

- [x] 1.3 Configure `WARRANTIES_DATA_DIR` outside the source checkout, restart the application process, and confirm its persistent files remain in that directory and are readable only by the owner/service account. — 2ce7e9e

### Phase 2: Daily Off-Host Backup and Restore

#### Automated

- [ ] 2.1 `uv run pytest tests/test_backup_restore.py` passes for consistent snapshot creation, mocked upload, integrity validation, safe restore, failure handling, and seven-copy retention.
- [ ] 2.2 `uv run pytest` passes the complete project test suite, including CLI argument and error-exit behavior.

#### Manual

- [ ] 2.3 Configure a private S3-compatible destination and a daily host schedule; create a backup, restore it into a clean replacement data root, and verify the database and every PDF match the source snapshot.