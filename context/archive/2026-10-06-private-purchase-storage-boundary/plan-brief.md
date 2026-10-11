# Private Profile Storage and Recovery — Plan Brief

> Full plan: `context/changes/private-purchase-storage-boundary/plan.md`

## What & Why

F-01 establishes persistent, owner-private storage for purchase metadata and PDF documents, then adds a usable recovery path for host or disk loss. It enables the first purchase-entry slices without implementing their fields, OCR, or user-facing flows.

## Starting Point

The Python package currently contains only a greeting command. FastAPI and Uvicorn are declared, but there is no database, PDF store, test suite, or deployment workflow; database and document storage are unselected.

## Desired End State

One owner's profile persists metadata in SQLite and PDFs in a private data directory, survives application restarts, and accepts files up to 20 MB. The expected personal-use envelope is one profile and up to 1,000 purchases; the purchase count is a capacity target, not a product cap.

A daily host-scheduled backup places a consistent database-and-document bundle in a private S3-compatible destination. Seven daily copies are retained. The restore command validates a bundle before restoring it to a replacement host; with the daily job succeeding, no more than 24 hours of changes are at risk.

## Key Decisions Made

| Decision | Choice | Why |
| -------- | ------ | --- |
| Initial scale | One profile, up to 1,000 purchases, PDFs up to 20 MB | Matches the personal local-profile MVP while bounding storage expectations. |
| Privacy boundary | One private owner profile; no accounts or shared access | The PRD puts accounts in the future and requires owner-only document visibility. |
| Persistence | SQLite metadata plus a private local PDF directory | Avoids operating separate live database and object-storage services for one profile. |
| Recovery | Daily off-host backup, host/disk-loss recovery, up to 24 hours of data loss | Makes the requested backup/restore requirement concrete and verifiable. |
| Retention | Seven daily backups | Keeps a short recovery history without introducing long-term retention policy. |

## Scope

**In scope:** private storage configuration, SQLite initialization, PDF file boundary, consistent backup archive with integrity manifest, S3-compatible upload, seven-copy retention, restore to a replacement host, tests, and operator runbook.

**Out of scope:** purchase CRUD/schema, OCR, warranty calculations, search, reminders, accounts, multi-tenant hosting, a hosting vendor choice, client-side encryption, multi-region recovery, and a restore-time SLA.

## Architecture / Approach

`WARRANTIES_DATA_DIR` contains `profile.sqlite3` and `documents/`. All storage writes share a cross-process lock. A CLI backup command snapshots both stores into one manifest-checked archive and uploads it to a private S3-compatible destination; a restore command validates the archive before activating it in an empty replacement data directory. The host scheduler invokes the command daily.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| ----- | ---------------- | -------- |
| 1. Private Profile Storage Boundary | A restart-persistent, private SQLite and PDF storage root with focused tests. | An unset or ephemeral data path could lose profile data. |
| 2. Daily Off-Host Backup and Restore | Consistent, validated daily backups, seven-copy retention, and replacement-host restore. | Host scheduling or destination credentials may be misconfigured. |

**Prerequisites:** A persistent owner-controlled data path, private S3-compatible bucket and credentials, and a host scheduler capable of daily command execution.
**Estimated effort:** Two implementation phases; no calendar estimate.

## Open Risks & Assumptions

- The deployment owner provides the S3-compatible endpoint, private bucket, credentials, and daily scheduler; no hosting provider is selected by this change.
- Destination-side encryption at rest and private object access protect backup copies; client-side encryption and multi-region disaster recovery are not included.
- The 24-hour recovery point assumes each daily backup succeeds; failures must surface through the command's non-zero exit and host scheduler logs.

## Success Criteria (Summary)

- Profile metadata and documents remain private and persist across application restarts.
- Automated tests verify consistent backup creation, integrity checking, safe restore, upload failure handling, and seven-copy retention.
- A manual recovery test restores a recent bundle to an empty replacement data directory and confirms the database and all PDFs match.