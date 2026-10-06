import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO
from urllib.parse import urlsplit
from uuid import uuid4

from warranties_10xdev.storage import (
    DATABASE_FILENAME,
    DOCUMENTS_DIRNAME,
    SOURCE_ROOT,
    ProfileStorage,
    StorageConfigurationError,
)

BACKUP_BUCKET_ENV = "WARRANTIES_BACKUP_BUCKET"
BACKUP_ENDPOINT_ENV = "WARRANTIES_BACKUP_ENDPOINT_URL"
BACKUP_REGION_ENV = "WARRANTIES_BACKUP_REGION"
BACKUP_PREFIX_ENV = "WARRANTIES_BACKUP_PREFIX"
MANIFEST_FILENAME = "manifest.json"
MANIFEST_VERSION = 1
BACKUP_PREFIX = "private-profile"
BACKUP_FILENAME_PREFIX = "profile-"
RETENTION_COUNT = 7
_BACKUP_KEY_PATTERN = re.compile(r"^profile-(\d{8}T\d{12}Z)-[0-9a-f]{12}\.zip$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MAX_MANIFEST_SIZE = 1024 * 1024


class BackupError(RuntimeError):
    """Base error for backup and restore failures."""


class BackupConfigurationError(BackupError):
    """Raised when object-storage configuration is incomplete or unsafe."""


class BackupIntegrityError(BackupError):
    """Raised when a backup archive is malformed, unsafe, or corrupt."""


@dataclass(frozen=True)
class BackupSettings:
    bucket: str
    region: str
    endpoint_url: str | None
    prefix: str = BACKUP_PREFIX

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> "BackupSettings":
        environment = os.environ if environ is None else environ
        bucket = environment.get(BACKUP_BUCKET_ENV, "").strip()
        region = environment.get(BACKUP_REGION_ENV, "").strip()
        endpoint_url = environment.get(BACKUP_ENDPOINT_ENV, "").strip() or None
        prefix = environment.get(BACKUP_PREFIX_ENV, BACKUP_PREFIX).strip().strip("/")

        missing = [
            name
            for name, value in ((BACKUP_BUCKET_ENV, bucket), (BACKUP_REGION_ENV, region))
            if not value
        ]
        if missing:
            raise BackupConfigurationError(
                "Required backup environment value(s) missing: " + ", ".join(missing)
            )
        if endpoint_url is not None:
            parsed_endpoint = urlsplit(endpoint_url)
            if (
                parsed_endpoint.scheme != "https"
                or not parsed_endpoint.netloc
                or parsed_endpoint.username is not None
                or parsed_endpoint.password is not None
                or parsed_endpoint.query
                or parsed_endpoint.fragment
            ):
                raise BackupConfigurationError(
                    f"{BACKUP_ENDPOINT_ENV} must be an HTTPS URL without embedded credentials or query data."
                )
        for endpoint_name in ("AWS_ENDPOINT_URL", "AWS_ENDPOINT_URL_S3"):
            configured_endpoint = environment.get(endpoint_name, "").strip()
            if configured_endpoint:
                parsed_endpoint = urlsplit(configured_endpoint)
                if parsed_endpoint.scheme != "https" or not parsed_endpoint.netloc:
                    raise BackupConfigurationError(
                        f"{endpoint_name} must be an HTTPS URL."
                    )
        return cls(bucket, region, endpoint_url, prefix)


def create_s3_client(settings: BackupSettings) -> Any:
    import boto3

    return boto3.client(
        "s3",
        region_name=settings.region,
        endpoint_url=settings.endpoint_url,
    )


def create_backup_archive(
    profile: ProfileStorage,
    archive_path: Path | str,
    *,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """Write a locked database/document snapshot and its integrity manifest."""
    output_path = Path(archive_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = _as_utc(created_at or datetime.now(timezone.utc))

    with tempfile.TemporaryDirectory(prefix="warranties-backup-") as temporary_dir:
        database_snapshot = Path(temporary_dir) / DATABASE_FILENAME
        hashes: dict[str, str] = {}
        with profile.lock:
            with closing(sqlite3.connect(profile.database_path)) as source:
                with closing(sqlite3.connect(database_snapshot)) as destination:
                    source.backup(destination)

            with zipfile.ZipFile(
                output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
            ) as archive:
                hashes[DATABASE_FILENAME] = _add_payload(
                    archive, database_snapshot, DATABASE_FILENAME
                )
                for document_path in sorted(profile.documents_dir.rglob("*")):
                    if document_path.is_symlink():
                        raise BackupError(
                            f"Symbolic links are not supported in private documents: {document_path}"
                        )
                    if document_path.is_dir():
                        continue
                    if not document_path.is_file():
                        raise BackupError(
                            f"Unsupported file in private documents: {document_path}"
                        )
                    relative_path = document_path.relative_to(profile.documents_dir)
                    archive_name = PurePosixPath(DOCUMENTS_DIRNAME, *relative_path.parts).as_posix()
                    _validate_payload_name(archive_name)
                    hashes[archive_name] = _add_payload(
                        archive, document_path, archive_name
                    )
                manifest = {
                    "version": MANIFEST_VERSION,
                    "created_at": timestamp.isoformat(),
                    "files": hashes,
                }
                archive.writestr(
                    MANIFEST_FILENAME,
                    json.dumps(manifest, sort_keys=True, separators=(",", ":")),
                )
    return manifest


def validate_backup_archive(archive_path: Path | str) -> dict[str, Any]:
    """Validate archive paths, manifest version, and every payload checksum."""
    path = Path(archive_path)
    try:
        with zipfile.ZipFile(path, "r") as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)):
                raise BackupIntegrityError("Backup archive contains duplicate paths.")
            by_name = {entry.filename: entry for entry in entries}
            manifest_entry = by_name.get(MANIFEST_FILENAME)
            if manifest_entry is None or manifest_entry.file_size > _MAX_MANIFEST_SIZE:
                raise BackupIntegrityError("Backup archive has no valid manifest.")
            _validate_zip_file(manifest_entry)
            manifest_data = archive.read(manifest_entry)
            manifest = json.loads(manifest_data.decode("utf-8"))
            files = _validate_manifest(manifest)
            expected_names = set(files) | {MANIFEST_FILENAME}
            if set(names) != expected_names:
                raise BackupIntegrityError(
                    "Backup archive contents do not match the manifest."
                )

            for name, expected_hash in files.items():
                entry = by_name[name]
                _validate_zip_file(entry)
                digest = hashlib.sha256()
                with archive.open(entry, "r") as payload:
                    for chunk in iter(lambda: payload.read(1024 * 1024), b""):
                        digest.update(chunk)
                if digest.hexdigest() != expected_hash:
                    raise BackupIntegrityError(f"Checksum mismatch for {name}.")
            return manifest
    except BackupIntegrityError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupIntegrityError(f"Could not validate backup archive: {exc}") from exc


def restore_backup_archive(archive_path: Path | str, data_root: Path | str) -> None:
    """Validate and stage a backup before replacing an empty profile directory."""
    root = _resolve_empty_data_root(data_root)
    manifest = validate_backup_archive(archive_path)
    parent = root.parent
    staging_root = Path(tempfile.mkdtemp(prefix=f".{root.name}-restore-", dir=parent))
    empty_root = parent / f".{root.name}-empty-{uuid4().hex}"
    try:
        os.chmod(staging_root, 0o700)
        with zipfile.ZipFile(archive_path, "r") as archive:
            for name in _validate_manifest(manifest):
                destination = staging_root.joinpath(*PurePosixPath(name).parts)
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with archive.open(name, "r") as source, destination.open("xb") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)

        (staging_root / DOCUMENTS_DIRNAME).mkdir(mode=0o700, exist_ok=True)
        ProfileStorage(staging_root)
        if any(root.iterdir()):
            raise BackupError("Restore target must remain empty until activation.")

        os.replace(root, empty_root)
        try:
            os.replace(staging_root, root)
        except OSError:
            os.replace(empty_root, root)
            raise
        shutil.rmtree(empty_root)
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)


def backup_to_s3(
    profile: ProfileStorage,
    client: Any,
    settings: BackupSettings,
    *,
    created_at: datetime | None = None,
) -> str:
    timestamp = _as_utc(created_at or datetime.now(timezone.utc))
    key = _backup_key(settings.prefix, timestamp)
    with tempfile.TemporaryDirectory(prefix="warranties-upload-") as temporary_dir:
        archive_path = Path(temporary_dir) / "profile.zip"
        create_backup_archive(profile, archive_path, created_at=timestamp)
        with archive_path.open("rb") as archive_file:
            client.put_object(
                Bucket=settings.bucket,
                Key=key,
                Body=archive_file,
                ACL="private",
                ServerSideEncryption="AES256",
                ContentType="application/zip",
            )

    prune_old_backups(client, settings)
    return f"s3://{settings.bucket}/{key}"


def restore_from_s3(
    client: Any,
    settings: BackupSettings,
    backup_reference: str,
    data_root: Path | str,
) -> None:
    bucket, key = _parse_backup_reference(backup_reference, settings.bucket)
    response = client.get_object(Bucket=bucket, Key=key)
    body = response["Body"]
    try:
        with tempfile.TemporaryDirectory(prefix="warranties-download-") as temporary_dir:
            download_path = Path(temporary_dir) / "backup.zip"
            with download_path.open("wb") as download:
                _copy_stream(body, download)
            restore_backup_archive(download_path, data_root)
    finally:
        close = getattr(body, "close", None)
        if close is not None:
            close()


def prune_old_backups(
    client: Any,
    settings: BackupSettings,
    *,
    keep: int = RETENTION_COUNT,
) -> list[str]:
    if keep < 1:
        raise ValueError("At least one valid backup must be retained.")
    prefix = _object_prefix(settings.prefix)
    listed: list[str] = []
    continuation_token: str | None = None
    while True:
        request: dict[str, Any] = {"Bucket": settings.bucket, "Prefix": prefix}
        if continuation_token is not None:
            request["ContinuationToken"] = continuation_token
        response = client.list_objects_v2(**request)
        listed.extend(
            item["Key"]
            for item in response.get("Contents", [])
            if _key_timestamp(item.get("Key", ""), prefix) is not None
        )
        if not response.get("IsTruncated"):
            break
        continuation_token = response.get("NextContinuationToken")
        if not continuation_token:
            raise BackupError("Object storage returned a truncated list without a token.")

    ordered_keys = sorted(
        set(listed), key=lambda item: _key_timestamp(item, prefix) or "", reverse=True
    )
    valid_keys: list[str] = []
    for key in ordered_keys:
        with tempfile.TemporaryDirectory(prefix="warranties-retention-") as temporary_dir:
            downloaded_path = Path(temporary_dir) / "backup.zip"
            response = client.get_object(Bucket=settings.bucket, Key=key)
            body = response["Body"]
            try:
                with downloaded_path.open("wb") as downloaded:
                    _copy_stream(body, downloaded)
                try:
                    validate_backup_archive(downloaded_path)
                except BackupIntegrityError:
                    continue
                valid_keys.append(key)
            finally:
                close = getattr(body, "close", None)
                if close is not None:
                    close()

    deleted: list[str] = []
    for key in valid_keys[keep:]:
        client.delete_object(Bucket=settings.bucket, Key=key)
        deleted.append(key)
    return deleted


def _add_payload(archive: zipfile.ZipFile, source_path: Path, name: str) -> str:
    digest = hashlib.sha256()
    with source_path.open("rb") as source, archive.open(name, "w") as destination:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
            destination.write(chunk)
    return digest.hexdigest()


def _copy_stream(source: BinaryIO, destination: BinaryIO) -> None:
    shutil.copyfileobj(source, destination, length=1024 * 1024)


def _validate_manifest(manifest: Any) -> dict[str, str]:
    if not isinstance(manifest, dict) or manifest.get("version") != MANIFEST_VERSION:
        raise BackupIntegrityError("Unsupported or malformed backup manifest version.")
    created_at = manifest.get("created_at")
    if not isinstance(created_at, str):
        raise BackupIntegrityError("Backup manifest has no creation timestamp.")
    try:
        parsed_timestamp = datetime.fromisoformat(created_at)
    except ValueError as exc:
        raise BackupIntegrityError("Backup manifest timestamp is invalid.") from exc
    if parsed_timestamp.tzinfo is None:
        raise BackupIntegrityError("Backup manifest timestamp must include a timezone.")

    files = manifest.get("files")
    if not isinstance(files, dict) or DATABASE_FILENAME not in files:
        raise BackupIntegrityError("Backup manifest must include the profile database.")
    validated: dict[str, str] = {}
    for name, digest in files.items():
        if not isinstance(name, str):
            raise BackupIntegrityError("Backup manifest contains a non-text path.")
        _validate_payload_name(name)
        if not isinstance(digest, str) or _SHA256_PATTERN.fullmatch(digest) is None:
            raise BackupIntegrityError(f"Backup manifest has an invalid SHA-256 for {name}.")
        validated[name] = digest
    return validated


def _validate_payload_name(name: str) -> None:
    if not name or "\\" in name or ":" in name or name.startswith("/"):
        raise BackupIntegrityError(f"Unsafe archive path: {name!r}.")
    path = PurePosixPath(name)
    if path.as_posix() != name or any(part in ("", ".", "..") for part in path.parts):
        raise BackupIntegrityError(f"Unsafe archive path: {name!r}.")
    if name != DATABASE_FILENAME and not name.startswith(f"{DOCUMENTS_DIRNAME}/"):
        raise BackupIntegrityError(f"Unexpected path in backup archive: {name!r}.")
    if name.startswith(f"{DOCUMENTS_DIRNAME}/") and len(path.parts) < 2:
        raise BackupIntegrityError(f"Invalid document path in backup archive: {name!r}.")


def _validate_zip_file(entry: zipfile.ZipInfo) -> None:
    if entry.is_dir():
        raise BackupIntegrityError(f"Unexpected directory entry: {entry.filename}.")
    mode = entry.external_attr >> 16
    file_type = stat.S_IFMT(mode)
    if file_type not in (0, stat.S_IFREG):
        raise BackupIntegrityError(f"Unsupported archive entry type: {entry.filename}.")


def _resolve_empty_data_root(data_root: Path | str) -> Path:
    raw_root = Path(data_root).expanduser()
    if raw_root.is_symlink():
        raise StorageConfigurationError("Restore target must not be a symbolic link.")
    try:
        root = raw_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise StorageConfigurationError(
            f"Restore target does not exist or cannot be resolved: {raw_root}"
        ) from exc
    if not root.is_dir():
        raise StorageConfigurationError(f"Restore target is not a directory: {root}")
    try:
        root.relative_to(SOURCE_ROOT.resolve())
    except ValueError:
        pass
    else:
        raise StorageConfigurationError(
            "WARRANTIES_DATA_DIR must resolve outside the source checkout."
        )
    if any(root.iterdir()):
        raise BackupError("Restore target must be an existing empty directory.")
    return root


def _as_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        raise ValueError("Backup timestamps must include a timezone.")
    return timestamp.astimezone(timezone.utc)


def _object_prefix(prefix: str) -> str:
    normalized = prefix.strip("/")
    return f"{normalized}/" if normalized else ""


def _backup_key(prefix: str, timestamp: datetime) -> str:
    filename = (
        f"{BACKUP_FILENAME_PREFIX}{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}-"
        f"{uuid4().hex[:12]}.zip"
    )
    return f"{_object_prefix(prefix)}{filename}"


def _key_timestamp(key: str, prefix: str) -> str | None:
    normalized_prefix = _object_prefix(prefix)
    if not key.startswith(normalized_prefix):
        return None
    match = _BACKUP_KEY_PATTERN.fullmatch(key[len(normalized_prefix) :])
    return match.group(1) if match else None


def _parse_backup_reference(reference: str, configured_bucket: str) -> tuple[str, str]:
    if reference.startswith("s3://"):
        parsed_reference = urlsplit(reference)
        if (
            parsed_reference.netloc != configured_bucket
            or not parsed_reference.path.startswith("/")
            or parsed_reference.query
            or parsed_reference.fragment
        ):
            raise BackupConfigurationError(
                "Backup reference must identify an object in the configured bucket."
            )
        key = parsed_reference.path.lstrip("/")
    else:
        key = reference
    if not key:
        raise BackupConfigurationError("Backup reference must include an object key.")
    return configured_bucket, key