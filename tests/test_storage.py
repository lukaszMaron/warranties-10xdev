import os
from pathlib import Path

import pytest

from warranties_10xdev import storage
from warranties_10xdev.storage import (
    DATA_DIR_ENV,
    MAX_PDF_SIZE_BYTES,
    ProfileStorage,
    StorageConfigurationError,
    validate_pdf_size,
)


@pytest.fixture(autouse=True)
def avoid_real_windows_acl_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.name == "nt":
        monkeypatch.setattr(
            storage.subprocess,
            "run",
            lambda *args, **kwargs: type(
                "Result", (), {"stdout": '"DOMAIN\\service","S-1-5-21-1"'}
            )(),
        )


def test_requires_configured_data_directory() -> None:
    with pytest.raises(StorageConfigurationError, match=DATA_DIR_ENV):
        ProfileStorage.from_environment({})


def test_rejects_missing_data_directory(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"

    with pytest.raises(StorageConfigurationError, match="does not exist"):
        ProfileStorage(missing_root)


def test_rejects_path_inside_source_checkout() -> None:
    with pytest.raises(StorageConfigurationError, match="outside the source checkout"):
        ProfileStorage.from_environment({DATA_DIR_ENV: str(storage.SOURCE_ROOT)})


def test_rejects_non_directory_data_path(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("", encoding="utf-8")

    with pytest.raises(StorageConfigurationError, match="not a directory"):
        ProfileStorage(file_path)


def test_rejects_unwritable_data_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = tmp_path / "profile"
    data_root.mkdir()

    def reject_write(*args: object, **kwargs: object) -> None:
        raise PermissionError("write denied")

    monkeypatch.setattr(storage.tempfile, "NamedTemporaryFile", reject_write)
    with pytest.raises(StorageConfigurationError, match="not writable"):
        ProfileStorage(data_root)


def test_initializes_private_paths_and_restricts_posix_permissions(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "profile"
    data_root.mkdir()

    profile = ProfileStorage.from_environment({DATA_DIR_ENV: str(data_root)})

    assert profile.database_path == data_root / "profile.sqlite3"
    assert profile.database_path.is_file()
    assert profile.documents_dir == data_root / "documents"
    assert profile.documents_dir.is_dir()
    assert profile.lock.lock_file == str(data_root / ".profile.lock")
    assert not profile.documents_dir.is_relative_to(storage.SOURCE_ROOT)
    if os.name == "posix":
        assert data_root.stat().st_mode & 0o777 == 0o700
        assert profile.documents_dir.stat().st_mode & 0o777 == 0o700
        assert profile.database_path.stat().st_mode & 0o777 == 0o600


def test_windows_initialization_restricts_all_private_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if os.name != "nt":
        pytest.skip("Windows ACL dispatch is platform-specific")

    data_root = tmp_path / "profile"
    data_root.mkdir()
    monkeypatch.setattr(storage, "_current_windows_user_sid", lambda: "S-1-5-21-1")
    calls: list[tuple[Path, str, bool]] = []
    monkeypatch.setattr(
        storage,
        "_apply_windows_acl",
        lambda path, sid, is_directory: calls.append((path, sid, is_directory)),
    )

    profile = ProfileStorage(data_root)

    assert calls == [
        (data_root, "S-1-5-21-1", True),
        (profile.documents_dir, "S-1-5-21-1", True),
        (profile.database_path, "S-1-5-21-1", False),
    ]


def test_windows_acl_replaces_permissions_and_grants_only_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "documents"
    calls: list[list[str]] = []

    def record_run(command: list[str], **kwargs: object) -> None:
        calls.append(command)

    monkeypatch.setattr(storage.subprocess, "run", record_run)

    storage._apply_windows_acl(path, "S-1-5-21-123", is_directory=True)
    storage._apply_windows_acl(path / "invoice.pdf", "S-1-5-21-123", is_directory=False)

    assert calls == [
        ["icacls.exe", str(path), "/reset"],
        ["icacls.exe", str(path), "/inheritance:r"],
        ["icacls.exe", str(path), "/grant:r", "*S-1-5-21-123:(OI)(CI)F"],
        ["icacls.exe", str(path / "invoice.pdf"), "/reset"],
        ["icacls.exe", str(path / "invoice.pdf"), "/inheritance:r"],
        ["icacls.exe", str(path / "invoice.pdf"), "/grant:r", "*S-1-5-21-123:F"],
    ]


def test_windows_acl_failure_raises_storage_configuration_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def reject_acl(command: list[str], **kwargs: object) -> None:
        raise storage.subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(storage.subprocess, "run", reject_acl)

    with pytest.raises(StorageConfigurationError, match="Windows storage permissions"):
        storage._apply_windows_acl(tmp_path, "S-1-5-21-123", is_directory=True)


def test_windows_owner_sid_is_read_from_effective_process_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def identify_user(command: list[str], **kwargs: object) -> object:
        return type("Result", (), {"stdout": '"DOMAIN\\service","S-1-5-21-123"'})()

    monkeypatch.setattr(storage.subprocess, "run", identify_user)

    assert storage._current_windows_user_sid() == "S-1-5-21-123"


def test_database_persists_after_reopening(tmp_path: Path) -> None:
    data_root = tmp_path / "profile"
    data_root.mkdir()
    profile = ProfileStorage(data_root)

    with profile.connect() as connection:
        connection.execute("CREATE TABLE storage_test (value TEXT NOT NULL)")
        connection.execute("INSERT INTO storage_test VALUES (?)", ("persisted",))

    reopened = ProfileStorage(data_root)
    with reopened.connect() as connection:
        row = connection.execute("SELECT value FROM storage_test").fetchone()

    assert row == ("persisted",)


def test_pdf_size_accepts_exact_limit_and_rejects_oversize() -> None:
    assert validate_pdf_size(MAX_PDF_SIZE_BYTES) is None

    with pytest.raises(ValueError, match="between 0"):
        validate_pdf_size(MAX_PDF_SIZE_BYTES + 1)


@pytest.mark.parametrize("size_bytes", [-1, True, 1.5])
def test_pdf_size_rejects_invalid_values(size_bytes: object) -> None:
    error = TypeError if isinstance(size_bytes, (bool, float)) else ValueError
    with pytest.raises(error):
        validate_pdf_size(size_bytes)  # type: ignore[arg-type]