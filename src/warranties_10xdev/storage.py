import csv
import io
import os
import re
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Mapping

from filelock import FileLock

DATA_DIR_ENV = "WARRANTIES_DATA_DIR"
DATABASE_FILENAME = "profile.sqlite3"
DOCUMENTS_DIRNAME = "documents"
MAX_PDF_SIZE_BYTES = 20 * 1024 * 1024
SOURCE_ROOT = Path(__file__).resolve().parents[2]


class StorageConfigurationError(ValueError):
    """Raised when the private profile storage root is not usable."""


class ProfileStorage:
    """Single-profile storage paths and SQLite/coordination primitives."""

    def __init__(self, data_root: Path | str) -> None:
        raw_root = Path(data_root).expanduser()
        try:
            self.data_root = raw_root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise StorageConfigurationError(
                f"Profile data directory does not exist or cannot be resolved: {raw_root}"
            ) from exc

        if not self.data_root.is_dir():
            raise StorageConfigurationError(
                f"Profile data path is not a directory: {self.data_root}"
            )
        if _is_within(self.data_root, SOURCE_ROOT):
            raise StorageConfigurationError(
                "WARRANTIES_DATA_DIR must resolve outside the source checkout."
            )

        self._windows_user_sid = (
            _current_windows_user_sid() if os.name == "nt" else None
        )
        self.database_path = self.data_root / DATABASE_FILENAME
        self.documents_dir = self.data_root / DOCUMENTS_DIRNAME
        self.lock = FileLock(str(self.data_root / ".profile.lock"))

        self._restrict_permissions(self.data_root, is_directory=True)
        self._check_writable()
        self._initialize_documents_dir()
        self._initialize_database()

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> "ProfileStorage":
        environment = os.environ if environ is None else environ
        configured_root = environment.get(DATA_DIR_ENV, "").strip()
        if not configured_root:
            raise StorageConfigurationError(
                f"{DATA_DIR_ENV} must be set to an existing persistent directory."
            )
        return cls(configured_root)

    def connect(self) -> sqlite3.Connection:
        """Open the profile database without creating application tables."""
        return sqlite3.connect(self.database_path)

    def _check_writable(self) -> None:
        try:
            with tempfile.NamedTemporaryFile(
                prefix=".warranties-write-check-", dir=self.data_root
            ):
                pass
        except OSError as exc:
            raise StorageConfigurationError(
                f"Profile data directory is not writable: {self.data_root}"
            ) from exc

    def _initialize_documents_dir(self) -> None:
        if self.documents_dir.is_symlink():
            raise StorageConfigurationError(
                f"Private documents path must not be a symbolic link: {self.documents_dir}"
            )
        try:
            self.documents_dir.mkdir(mode=0o700, exist_ok=True)
            if not self.documents_dir.is_dir():
                raise StorageConfigurationError(
                    f"Private documents path is not a directory: {self.documents_dir}"
                )
            self._restrict_permissions(self.documents_dir, is_directory=True)
        except OSError as exc:
            raise StorageConfigurationError(
                f"Could not initialize private documents directory: {self.documents_dir}"
            ) from exc

    def _initialize_database(self) -> None:
        if self.database_path.is_symlink():
            raise StorageConfigurationError(
                f"Profile database path must not be a symbolic link: {self.database_path}"
            )
        if self.database_path.exists() and not self.database_path.is_file():
            raise StorageConfigurationError(
                f"Profile database path is not a regular file: {self.database_path}"
            )
        try:
            connection = self.connect()
            connection.close()
            self._restrict_permissions(self.database_path, is_directory=False)
        except (OSError, sqlite3.Error) as exc:
            raise StorageConfigurationError(
                f"Could not initialize profile database: {self.database_path}"
            ) from exc

    def _restrict_permissions(self, path: Path, *, is_directory: bool) -> None:
        if os.name == "posix":
            try:
                path.chmod(0o700 if is_directory else 0o600)
            except OSError as exc:
                raise StorageConfigurationError(
                    f"Could not restrict storage permissions: {path}"
                ) from exc
        elif os.name == "nt":
            if self._windows_user_sid is None:
                raise StorageConfigurationError(
                    "Could not identify the Windows profile storage owner."
                )
            _apply_windows_acl(path, self._windows_user_sid, is_directory)


def _current_windows_user_sid() -> str:
    try:
        result = subprocess.run(
            ["whoami.exe", "/user", "/fo", "csv", "/nh"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        rows = list(csv.reader(io.StringIO(result.stdout)))
    except (OSError, subprocess.SubprocessError, csv.Error) as exc:
        raise StorageConfigurationError(
            "Could not identify the Windows profile storage owner."
        ) from exc

    if (
        len(rows) != 1
        or len(rows[0]) != 2
        or re.fullmatch(r"S-\d+(?:-\d+)+", rows[0][1]) is None
    ):
        raise StorageConfigurationError(
            "Could not identify the Windows profile storage owner."
        )
    return rows[0][1]


def _apply_windows_acl(path: Path, owner_sid: str, is_directory: bool) -> None:
    inheritance = "(OI)(CI)F" if is_directory else "F"
    commands = (
        ["icacls.exe", str(path), "/reset"],
        ["icacls.exe", str(path), "/inheritance:r"],
        ["icacls.exe", str(path), "/grant:r", f"*{owner_sid}:{inheritance}"],
    )
    try:
        for command in commands:
            subprocess.run(command, check=True, capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise StorageConfigurationError(
            f"Could not restrict Windows storage permissions: {path}"
        ) from exc


def validate_pdf_size(size_bytes: int) -> None:
    """Reject PDF payload sizes outside the inclusive 20 MiB limit."""
    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int):
        raise TypeError("PDF size must be an integer number of bytes.")
    if size_bytes < 0 or size_bytes > MAX_PDF_SIZE_BYTES:
        raise ValueError(f"PDF size must be between 0 and {MAX_PDF_SIZE_BYTES} bytes.")


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent.resolve())
    except ValueError:
        return False
    return True