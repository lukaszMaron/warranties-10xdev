import io
import hashlib
import json
import os
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from warranties_10xdev import backup, cli, storage
from warranties_10xdev.backup import (
    BACKUP_PREFIX,
    BackupError,
    BackupIntegrityError,
    BackupSettings,
    backup_to_s3,
    create_backup_archive,
    prune_old_backups,
    restore_backup_archive,
    validate_backup_archive,
)
from warranties_10xdev.storage import DATA_DIR_ENV, ProfileStorage


@pytest.fixture(autouse=True)
def avoid_real_windows_acl_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.name == "nt":
        monkeypatch.setattr(storage, "_current_windows_user_sid", lambda: "S-1-5-21-1")
        monkeypatch.setattr(storage, "_apply_windows_acl", lambda *args: None)


def _profile(root: Path) -> ProfileStorage:
    root.mkdir()
    profile = ProfileStorage(root)
    with profile.connect() as connection:
        connection.execute("CREATE TABLE purchase (description TEXT NOT NULL)")
        connection.execute("INSERT INTO purchase VALUES (?)", ("camera",))
    (profile.documents_dir / "invoice.pdf").write_bytes(b"pdf contents")
    (profile.documents_dir / "nested").mkdir()
    (profile.documents_dir / "nested" / "receipt.pdf").write_bytes(b"receipt")
    return profile


class StubS3:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []
        self.fail_put = False

    def put_object(self, **request: Any) -> None:
        if self.fail_put:
            raise OSError("upload failed")
        self.objects[request["Key"]] = request["Body"].read()
        assert request["ACL"] == "private"
        assert request["ServerSideEncryption"] == "AES256"

    def list_objects_v2(self, **request: Any) -> dict[str, Any]:
        keys = sorted(key for key in self.objects if key.startswith(request["Prefix"]))
        return {"Contents": [{"Key": key} for key in keys], "IsTruncated": False}

    def get_object(self, **request: Any) -> dict[str, Any]:
        return {"Body": io.BytesIO(self.objects[request["Key"]])}

    def delete_object(self, **request: Any) -> None:
        self.deleted.append(request["Key"])
        del self.objects[request["Key"]]


def _settings() -> BackupSettings:
    return BackupSettings("private-bucket", "test-region-1", None, BACKUP_PREFIX)


def _archive_bytes(profile: ProfileStorage, path: Path, timestamp: datetime) -> bytes:
    create_backup_archive(profile, path, created_at=timestamp)
    return path.read_bytes()


def test_archive_manifest_hashes_and_restore_preserve_profile_snapshot(
    tmp_path: Path,
) -> None:
    profile = _profile(tmp_path / "source")
    archive_path = tmp_path / "profile.zip"
    created_at = datetime(2026, 10, 1, tzinfo=timezone.utc)

    manifest = create_backup_archive(profile, archive_path, created_at=created_at)
    assert manifest["version"] == 1
    assert manifest["created_at"] == created_at.isoformat()
    assert set(manifest["files"]) == {
        "profile.sqlite3",
        "documents/invoice.pdf",
        "documents/nested/receipt.pdf",
    }
    assert validate_backup_archive(archive_path) == manifest

    replacement = tmp_path / "replacement"
    replacement.mkdir()
    restore_backup_archive(archive_path, replacement)

    restored = ProfileStorage(replacement)
    with restored.connect() as connection:
        assert connection.execute("SELECT description FROM purchase").fetchall() == [
            ("camera",)
        ]
    assert (replacement / "documents" / "invoice.pdf").read_bytes() == b"pdf contents"
    assert (
        replacement / "documents" / "nested" / "receipt.pdf"
    ).read_bytes() == b"receipt"


def test_restore_rejects_path_traversal_without_extracting_files(tmp_path: Path) -> None:
    malicious_archive = tmp_path / "traversal.zip"
    payload = b"outside"
    manifest = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": {
            "documents/../outside.txt": hashlib.sha256(payload).hexdigest(),
            "profile.sqlite3": hashlib.sha256(b"database").hexdigest(),
        },
    }
    with zipfile.ZipFile(malicious_archive, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("documents/../outside.txt", payload)
        archive.writestr("profile.sqlite3", b"database")

    replacement = tmp_path / "replacement"
    replacement.mkdir()
    with pytest.raises(BackupIntegrityError, match="Unsafe archive path"):
        restore_backup_archive(malicious_archive, replacement)

    assert list(replacement.iterdir()) == []
    assert not (tmp_path / "outside.txt").exists()


def test_restore_rejects_corrupt_payload_and_non_empty_target(tmp_path: Path) -> None:
    profile = _profile(tmp_path / "source")
    valid_archive = tmp_path / "valid.zip"
    create_backup_archive(profile, valid_archive)
    with zipfile.ZipFile(valid_archive, "r") as source:
        entries = {entry.filename: source.read(entry.filename) for entry in source.infolist()}
    corrupted_archive = tmp_path / "corrupt.zip"
    entries["documents/invoice.pdf"] = b"tampered"
    with zipfile.ZipFile(corrupted_archive, "w") as destination:
        for name, contents in entries.items():
            destination.writestr(name, contents)

    replacement = tmp_path / "replacement"
    replacement.mkdir()
    with pytest.raises(BackupIntegrityError, match="Checksum mismatch"):
        restore_backup_archive(corrupted_archive, replacement)
    assert list(replacement.iterdir()) == []

    (replacement / "keep.txt").write_text("active", encoding="utf-8")
    with pytest.raises(BackupError, match="existing empty directory"):
        restore_backup_archive(valid_archive, replacement)
    assert (replacement / "keep.txt").read_text(encoding="utf-8") == "active"
    with profile.connect() as connection:
        assert connection.execute("SELECT description FROM purchase").fetchone() == (
            "camera",
        )


def test_failed_upload_preserves_previous_remote_backup(tmp_path: Path) -> None:
    profile = _profile(tmp_path / "source")
    client = StubS3()
    prior_key = f"{BACKUP_PREFIX}/profile-20260930T020000000000Z-000000000001.zip"
    client.objects[prior_key] = b"known-good-backup"
    client.fail_put = True

    with pytest.raises(OSError, match="upload failed"):
        backup_to_s3(profile, client, _settings())

    assert client.objects == {prior_key: b"known-good-backup"}
    assert client.deleted == []


def test_successful_upload_retains_seven_newest_valid_backups(
    tmp_path: Path,
) -> None:
    profile = _profile(tmp_path / "source")
    client = StubS3()
    base_time = datetime(2026, 9, 20, 2, tzinfo=timezone.utc)
    for day_offset in range(8):
        timestamp = base_time + timedelta(days=day_offset)
        archive_path = tmp_path / f"backup-{day_offset}.zip"
        key = (
            f"{BACKUP_PREFIX}/profile-"
            f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}-{day_offset:012x}.zip"
        )
        client.objects[key] = _archive_bytes(profile, archive_path, timestamp)

    latest_time = base_time + timedelta(days=8)
    uploaded_reference = backup_to_s3(
        profile, client, _settings(), created_at=latest_time
    )

    assert uploaded_reference.startswith("s3://private-bucket/")
    assert len(client.objects) == 7
    assert len(client.deleted) == 2
    assert validate_backup_archive(tmp_path / "backup-0.zip")["version"] == 1
    assert all(
        backup._key_timestamp(key, BACKUP_PREFIX) is not None for key in client.objects
    )


def test_retention_skips_invalid_archives_and_keeps_them_untouched() -> None:
    client = StubS3()
    settings = _settings()
    invalid_key = f"{BACKUP_PREFIX}/profile-20260901T020000000000Z-000000000001.zip"
    client.objects[invalid_key] = b"not a zip archive"

    assert prune_old_backups(client, settings) == []
    assert client.objects[invalid_key] == b"not a zip archive"


def test_cli_backup_and_nonzero_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profile_root = tmp_path / "profile"
    _profile(profile_root)
    monkeypatch.setenv(DATA_DIR_ENV, str(profile_root))
    monkeypatch.setenv("WARRANTIES_BACKUP_BUCKET", "private-bucket")
    monkeypatch.setenv("WARRANTIES_BACKUP_REGION", "test-region-1")
    client = StubS3()
    monkeypatch.setattr(cli, "create_s3_client", lambda settings: client)

    assert cli.main(["backup"]) == 0
    backup_reference = next(iter(client.objects))
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    monkeypatch.setenv(DATA_DIR_ENV, str(replacement))
    assert cli.main(["restore", f"s3://private-bucket/{backup_reference}"]) == 0
    restored = ProfileStorage(replacement)
    with restored.connect() as connection:
        assert connection.execute("SELECT description FROM purchase").fetchone() == (
            "camera",
        )
    assert (replacement / "documents" / "invoice.pdf").read_bytes() == b"pdf contents"

    monkeypatch.setenv(DATA_DIR_ENV, str(profile_root))
    client.fail_put = True
    assert cli.main(["backup"]) == 1
    with pytest.raises(SystemExit) as error:
        cli.main(["restore"])
    assert error.value.code == 2


def test_backup_settings_reject_insecure_custom_endpoint() -> None:
    with pytest.raises(backup.BackupConfigurationError, match="HTTPS"):
        BackupSettings.from_environment(
            {
                "WARRANTIES_BACKUP_BUCKET": "private-bucket",
                "WARRANTIES_BACKUP_REGION": "test-region-1",
                "WARRANTIES_BACKUP_ENDPOINT_URL": "http://storage.example.test",
            }
        )

    with pytest.raises(backup.BackupConfigurationError, match="AWS_ENDPOINT_URL_S3"):
        BackupSettings.from_environment(
            {
                "WARRANTIES_BACKUP_BUCKET": "private-bucket",
                "WARRANTIES_BACKUP_REGION": "test-region-1",
                "AWS_ENDPOINT_URL_S3": "http://storage.example.test",
            }
        )