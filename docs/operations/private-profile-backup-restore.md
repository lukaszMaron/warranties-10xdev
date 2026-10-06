# Private Profile Backup and Restore

The `warranties-10xdev backup` command snapshots `profile.sqlite3` and the complete `documents/` tree under the profile lock, then uploads one versioned archive. Run it from a host scheduler, separately from the web process. The command exits non-zero when configuration, upload, validation, or retention fails.

## Required Configuration

Set these values in the scheduler's protected environment:

| Variable | Required | Purpose |
| --- | --- | --- |
| `WARRANTIES_DATA_DIR` | Yes | Existing persistent profile directory. |
| `WARRANTIES_BACKUP_BUCKET` | Yes | Private S3-compatible bucket name. |
| `WARRANTIES_BACKUP_REGION` | Yes | S3 region used by the client. |
| `WARRANTIES_BACKUP_ENDPOINT_URL` | No | Custom endpoint; when set it must use HTTPS. Omit for the AWS endpoint. |
| `WARRANTIES_BACKUP_PREFIX` | No | Object key prefix; defaults to `private-profile`. |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Depends | Credentials supplied through the AWS environment provider. `AWS_SESSION_TOKEN` may also be set. A host identity/role provider may be used instead. |

Use credentials scoped to this bucket and only the required list, read, write, and delete operations. Keep secrets in the host's secret/environment facility or a mode-`0600` environment file readable only by the service account; never commit them or place them in the scheduler command line. The bucket must block public access, require TLS, and have destination-side encryption at rest enabled. Uploads explicitly request a private object ACL and AES-256 server-side encryption.

## Daily Scheduling

Install and lock the project dependencies on the host, then schedule the installed console command daily as the profile service account. For a cron-based host, a protected environment file can be loaded by a wrapper that runs:

```sh
set -a
. /etc/warranties-backup.env
set +a
/srv/warranties/.venv/bin/warranties-10xdev backup
```

Add the wrapper to the host's crontab once per day at a quiet time, for example:

```cron
15 2 * * * /usr/local/sbin/warranties-backup >> /var/log/warranties-backup.log 2>&1
```

Send stdout and stderr to the host's normal job log, and configure the scheduler to alert on any non-zero exit. Check the latest successful object in the configured bucket and periodically perform a restore drill. Each successful run retains the seven newest valid archives; retention runs only after the new archive has uploaded.

## Restore to a Replacement Host

1. Install the same or a compatible application release and configure the backup bucket, region, endpoint, and read credentials.
2. Create the replacement `WARRANTIES_DATA_DIR` as an existing empty directory outside the source checkout. Stop any application process that could write to it.
3. Run `warranties-10xdev restore s3://<bucket>/<object-key>` using the replacement host's protected environment.
4. Start the application and verify the restored database and all expected PDFs before directing traffic to the host.

Restore validates the manifest, payload hashes, archive entry types, and paths in a staging directory before activation. It refuses a missing, non-directory, symlink, or non-empty target. Keep the source host and its data intact until the replacement has been checked.

## Recovery Expectations

The daily schedule assumes a maximum of 24 hours of data loss, provided the scheduled backup completed successfully. A failed or skipped job can exceed that window, so scheduler failure alerts and restore drills are part of the recovery process. Seven valid daily recovery points are retained; no continuous or point-in-time recovery is provided.