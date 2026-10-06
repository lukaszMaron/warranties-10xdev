import argparse
import os
import sys
from collections.abc import Sequence

from warranties_10xdev.backup import (
    BackupConfigurationError,
    BackupError,
    BackupSettings,
    backup_to_s3,
    create_s3_client,
    restore_from_s3,
)
from warranties_10xdev.storage import DATA_DIR_ENV, ProfileStorage, StorageConfigurationError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="warranties-10xdev")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("backup", help="create and upload a profile backup")
    restore = commands.add_parser("restore", help="restore a profile backup")
    restore.add_argument("backup_reference")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        settings = BackupSettings.from_environment()
        client = create_s3_client(settings)
        if arguments.command == "backup":
            reference = backup_to_s3(
                ProfileStorage.from_environment(), client, settings
            )
            print(f"Backup created: {reference}")
        else:
            data_root = os.environ.get(DATA_DIR_ENV, "").strip()
            if not data_root:
                raise StorageConfigurationError(
                    f"{DATA_DIR_ENV} must be set to an existing empty persistent directory."
                )
            restore_from_s3(
                client, settings, arguments.backup_reference, data_root
            )
            print(f"Profile restored from {arguments.backup_reference}")
    except (BackupError, StorageConfigurationError, OSError, RuntimeError) as exc:
        print(f"warranties-10xdev {arguments.command} failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"warranties-10xdev {arguments.command} failed: {exc}", file=sys.stderr)
        return 1
    return 0