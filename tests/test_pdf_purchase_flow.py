from datetime import date, datetime, timedelta, timezone, tzinfo
import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from warranties_10xdev import api, purchases, storage
from warranties_10xdev.purchases import (
    PurchaseInput,
    PurchaseSaveError,
    PurchaseValidationError,
    save_purchase,
)
from warranties_10xdev.storage import ProfileStorage

client = TestClient(api.app)


@pytest.fixture(autouse=True)
def avoid_real_windows_acl_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.name == "nt":
        monkeypatch.setattr(storage, "_current_windows_user_sid", lambda: "S-1-5-21-1")
        monkeypatch.setattr(storage, "_apply_windows_acl", lambda *args: None)


def _pdf() -> bytes:
    content = b"BT /F1 12 Tf 72 720 Td (Synthetic receipt) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + body + b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    output.extend(b"".join(f"{offset:010} 00000 n \n".encode() for offset in offsets[1:]))
    output.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    )
    return bytes(output)


def _profile(root: Path) -> ProfileStorage:
    root.mkdir()
    return ProfileStorage(root)


def _purchase(**overrides: object) -> PurchaseInput:
    values: dict[str, object] = {
        "product_name": "Corrected drill name",
        "purchase_date": date(2025, 4, 3),
        "purchase_type": "private",
        "seller": "Tool shop",
        "payment_method": "Card",
        "warranty_end_date": date(2027, 4, 3),
    }
    values.update(overrides)
    return PurchaseInput(**values)  # type: ignore[arg-type]


def test_save_persists_corrected_values_and_private_pdf_after_reopen(
    tmp_path: Path,
) -> None:
    profile = _profile(tmp_path / "profile")
    saved = save_purchase(
        profile,
        _purchase(product_name="User correction"),
        _pdf(),
    )

    reopened = ProfileStorage(profile.data_root)
    with reopened.connect() as connection:
        row = connection.execute(
            "SELECT product_name, purchase_date, purchase_type, seller, payment_method, "
            "warranty_end_date, document_ref FROM purchase WHERE purchase_id = ?",
            (saved.purchase_id,),
        ).fetchone()

    assert row == (
        "User correction",
        "2025-04-03",
        "private",
        "Tool shop",
        "Card",
        "2027-04-03",
        saved.document_ref,
    )
    assert Path(saved.document_ref).name == saved.document_ref
    assert not Path(saved.document_ref).is_absolute()
    assert "/" not in saved.document_ref and "\\" not in saved.document_ref
    assert (reopened.documents_dir / saved.document_ref).read_bytes() == _pdf()
    assert not list(reopened.data_root.glob(".purchase-*.tmp"))


def test_save_purchase_without_pdf_creates_only_a_database_row(tmp_path: Path) -> None:
    profile = _profile(tmp_path / "profile")

    saved = save_purchase(profile, _purchase())

    assert saved.document_ref is None
    with profile.connect() as connection:
        row = connection.execute(
            "SELECT product_name, document_ref FROM purchase WHERE purchase_id = ?",
            (saved.purchase_id,),
        ).fetchone()
        document_column = next(
            column
            for column in connection.execute("PRAGMA table_info(purchase)").fetchall()
            if column[1] == "document_ref"
        )
    assert row == ("Corrected drill name", None)
    assert document_column[3] == 0
    assert list(profile.documents_dir.iterdir()) == []
    assert not list(profile.data_root.glob(".purchase-*.tmp"))


def test_save_migrates_legacy_purchase_table_without_changing_pdf_or_values(
    tmp_path: Path,
) -> None:
    profile = _profile(tmp_path / "profile")
    document_ref = "s01-purchase.pdf"
    original_pdf = _pdf()
    (profile.documents_dir / document_ref).write_bytes(original_pdf)
    with profile.connect() as connection:
        connection.execute(
            """
            CREATE TABLE purchase (
                purchase_id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                purchase_date TEXT NOT NULL,
                purchase_type TEXT NOT NULL CHECK (purchase_type IN ('private', 'business')),
                seller TEXT,
                payment_method TEXT,
                warranty_end_date TEXT,
                document_ref TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO purchase VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "s01-purchase",
                "Existing drill",
                "2024-03-04",
                "business",
                "Existing seller",
                "Bank transfer",
                "2026-03-04",
                document_ref,
                "2024-03-04T12:30:00+00:00",
            ),
        )

    manual = save_purchase(profile, _purchase(), None)
    second_manual = save_purchase(profile, _purchase(product_name="Second manual"))

    with profile.connect() as connection:
        existing = connection.execute(
            "SELECT purchase_id, product_name, purchase_date, purchase_type, seller, "
            "payment_method, warranty_end_date, document_ref, created_at "
            "FROM purchase WHERE purchase_id = 's01-purchase'"
        ).fetchone()
        references = connection.execute(
            "SELECT document_ref FROM purchase WHERE document_ref IS NOT NULL"
        ).fetchall()
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE purchase SET document_ref = ? WHERE purchase_id = ?",
                (document_ref, manual.purchase_id),
            )

    assert existing == (
        "s01-purchase",
        "Existing drill",
        "2024-03-04",
        "business",
        "Existing seller",
        "Bank transfer",
        "2026-03-04",
        document_ref,
        "2024-03-04T12:30:00+00:00",
    )
    assert references == [(document_ref,)]
    assert manual.document_ref is None
    assert second_manual.document_ref is None
    assert (profile.documents_dir / document_ref).read_bytes() == original_pdf
    assert sorted(path.name for path in profile.documents_dir.iterdir()) == [document_ref]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"product_name": "   "}, "Product name is required"),
        ({"purchase_type": "other"}, "Purchase type must be private or business"),
    ],
)
def test_save_rejects_invalid_required_values(
    tmp_path: Path, overrides: dict[str, object], message: str
) -> None:
    profile = _profile(tmp_path / "profile")

    with pytest.raises(PurchaseValidationError, match=message):
        save_purchase(profile, _purchase(**overrides), _pdf())

    assert list(profile.documents_dir.iterdir()) == []


def test_database_insert_failure_cleans_staged_pdf_and_keeps_no_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = _profile(tmp_path / "profile")

    def fail_insert(*args: object, **kwargs: object) -> None:
        raise sqlite3.IntegrityError("injected insert failure")

    monkeypatch.setattr(purchases, "_insert_purchase", fail_insert)

    with pytest.raises(PurchaseSaveError):
        save_purchase(profile, _purchase(), _pdf())

    with profile.connect() as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'purchase'"
        ).fetchone() is None
    assert list(profile.documents_dir.iterdir()) == []
    assert not list(profile.data_root.glob(".purchase-*.tmp"))


def test_file_promotion_failure_rolls_back_database_and_cleans_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = _profile(tmp_path / "profile")

    def fail_promotion(staged_path: Path, document_path: Path) -> None:
        raise OSError("injected promotion failure")

    monkeypatch.setattr(purchases, "_promote_staged_file", fail_promotion)

    with pytest.raises(PurchaseSaveError):
        save_purchase(profile, _purchase(), _pdf())

    with profile.connect() as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'purchase'"
        ).fetchone() is None
    assert list(profile.documents_dir.iterdir()) == []
    assert not list(profile.data_root.glob(".purchase-*.tmp"))


def test_api_saves_corrected_values_and_private_pdf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = tmp_path / "profile"
    data_root.mkdir()
    monkeypatch.setenv(storage.DATA_DIR_ENV, str(data_root))
    monkeypatch.setattr(api, "utc_today", lambda: date(2026, 10, 17))

    response = client.post(
        "/api/purchases",
        data={
            "product_name": "Corrected after OCR",
            "purchase_date": "2025-04-03",
            "purchase_type": "business",
            "seller": "Tool shop",
            "payment_method": "Card",
            "warranty_end_date": "2027-04-03",
        },
        files={"file": ("invoice.pdf", _pdf(), "application/pdf")},
    )

    assert response.status_code == 200
    saved = response.json()
    assert saved["product_name"] == "Corrected after OCR"
    assert saved["purchase_date"] == "2025-04-03"
    assert saved["purchase_type"] == "business"
    assert saved["seller"] == "Tool shop"
    assert saved["payment_method"] == "Card"
    assert saved["warranty_end_date"] == "2027-04-03"
    assert saved["effective_end_date"] == "2027-04-03"
    assert saved["date_basis"] == "user"
    assert saved["status"] == "active"
    assert saved["document_ref"].endswith(".pdf")
    assert "url" not in saved and str(data_root) not in response.text

    profile = ProfileStorage(data_root)
    with profile.connect() as connection:
        assert connection.execute(
            "SELECT product_name FROM purchase WHERE purchase_id = ?",
            (saved["purchase_id"],),
        ).fetchone() == ("Corrected after OCR",)
    assert (profile.documents_dir / saved["document_ref"]).read_bytes() == _pdf()


def test_api_accepts_manual_completion_without_preview(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = tmp_path / "profile"
    data_root.mkdir()
    monkeypatch.setenv(storage.DATA_DIR_ENV, str(data_root))

    response = client.post(
        "/api/purchases",
        data={
            "product_name": "Manually entered product",
            "purchase_date": "2025-04-03",
            "purchase_type": "private",
            "warranty_end_date": "",
        },
    )

    assert response.status_code == 200
    saved = response.json()
    assert saved["product_name"] == "Manually entered product"
    assert saved["seller"] is None
    assert saved["payment_method"] is None
    assert saved["warranty_end_date"] is None
    assert saved["warranty_end_date"] is None
    assert saved["document_ref"] is None
    assert saved["effective_end_date"] == "2027-04-03"
    assert saved["date_basis"] == "estimate"
    assert saved["status"] in {"active", "expired"}


def test_api_reports_manual_save_failure_without_pdf_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = tmp_path / "profile"
    data_root.mkdir()
    monkeypatch.setenv(storage.DATA_DIR_ENV, str(data_root))

    def fail_insert(*args: object, **kwargs: object) -> None:
        raise sqlite3.IntegrityError("injected insert failure")

    monkeypatch.setattr(purchases, "_insert_purchase", fail_insert)
    response = client.post(
        "/api/purchases",
        data={
            "product_name": "Manually entered product",
            "purchase_date": "2025-04-03",
            "purchase_type": "private",
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "The purchase could not be saved."


def test_api_returns_manual_warranty_override_as_user_provided(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = tmp_path / "profile"
    data_root.mkdir()
    monkeypatch.setenv(storage.DATA_DIR_ENV, str(data_root))

    response = client.post(
        "/api/purchases",
        data={
            "product_name": "Manually entered product",
            "purchase_date": "2025-04-03",
            "purchase_type": "private",
            "warranty_end_date": "2099-08-09",
        },
    )

    assert response.status_code == 200
    saved = response.json()
    assert saved["warranty_end_date"] == "2099-08-09"
    assert saved["effective_end_date"] == "2099-08-09"
    assert saved["date_basis"] == "user"
    assert saved["status"] == "active"


@pytest.mark.parametrize(
    ("purchase_type", "end_date", "effective_end_date", "expected_message"),
    [
        (
            "private", "2026-03-09", "2026-03-09",
            "Warranty end date is earlier than the purchase date.",
        ),
        (
            "business", "2027-06-01", "2027-06-01",
            "Warranty end date is later than the estimated 1-year business warranty (2027-03-10).",
        ),
        ("private", "2027-06-01", "2027-06-01", None),
        (
            "private", "2099-08-09", "2099-08-09",
            "Warranty end date is later than the estimated 2-year private warranty (2028-03-10).",
        ),
        ("business", "", "2027-03-10", None),
    ],
)
def test_api_persists_warranty_dates_and_returns_nonblocking_warnings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    purchase_type: str,
    end_date: str,
    effective_end_date: str,
    expected_message: str | None,
) -> None:
    # Research decision 3: warn without rejecting or changing the manual date.
    data_root = tmp_path / "profile"
    data_root.mkdir()
    monkeypatch.setenv(storage.DATA_DIR_ENV, str(data_root))

    response = client.post(
        "/api/purchases",
        data={
            "product_name": "Manual warranty",
            "purchase_date": "2026-03-10",
            "purchase_type": purchase_type,
            "warranty_end_date": end_date,
        },
    )

    assert response.status_code == 200
    saved = response.json()
    assert saved["warnings"] == (
        {"warranty_end_date": expected_message} if expected_message is not None else {}
    )
    assert saved["warranty_end_date"] == (end_date or None)
    assert saved["effective_end_date"] == effective_end_date
    assert saved["date_basis"] == ("user" if end_date else "estimate")
    with ProfileStorage(data_root).connect() as connection:
        assert connection.execute(
            "SELECT purchase_type, warranty_end_date FROM purchase WHERE purchase_id = ?",
            (saved["purchase_id"],),
        ).fetchone() == (purchase_type, end_date or None)


def test_api_clock_uses_utc_date_when_device_is_already_on_next_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Research decision 4: Warsaw 2026-10-18 00:30 is still 2026-10-17 in UTC.
    device_timezone = timezone(timedelta(hours=2))
    instant = datetime(2026, 10, 18, 0, 30, tzinfo=device_timezone)

    class FixedClock:
        @staticmethod
        def now(tz: tzinfo | None = None) -> datetime:
            return instant.astimezone(tz if tz is not None else device_timezone)

    monkeypatch.setattr(api, "datetime", FixedClock)

    assert api.utc_today() == date(2026, 10, 17)


@pytest.mark.parametrize(
    ("utc_date", "expected_status"),
    [(date(2026, 10, 17), "active"), (date(2026, 10, 18), "expired")],
)
def test_api_warranty_end_is_inclusive_using_utc_clock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    utc_date: date,
    expected_status: str,
) -> None:
    data_root = tmp_path / "profile"
    data_root.mkdir()
    monkeypatch.setenv(storage.DATA_DIR_ENV, str(data_root))
    monkeypatch.setattr(api, "utc_today", lambda: utc_date)

    response = client.post(
        "/api/purchases",
        data={
            "product_name": "UTC boundary",
            "purchase_date": "2025-10-17",
            "purchase_type": "business",
            "warranty_end_date": "2026-10-17",
        },
    )

    assert response.status_code == 200
    saved = response.json()
    assert saved["status"] == expected_status
    assert saved["effective_end_date"] == "2026-10-17"
    assert saved["date_basis"] == "user"
    assert saved["warnings"] == {}


def test_api_rejects_missing_required_fields_and_corrupt_pdf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = tmp_path / "profile"
    data_root.mkdir()
    monkeypatch.setenv(storage.DATA_DIR_ENV, str(data_root))

    missing_field = client.post(
        "/api/purchases",
        data={"product_name": "Drill", "purchase_type": "private"},
    )
    corrupt_pdf = client.post(
        "/api/purchases",
        data={
            "product_name": "Drill",
            "purchase_date": "2025-04-03",
            "purchase_type": "private",
        },
        files={"file": ("receipt.pdf", b"%PDF-corrupt", "application/pdf")},
    )

    assert missing_field.status_code == 422
    assert corrupt_pdf.status_code == 422
    assert list(data_root.joinpath(storage.DOCUMENTS_DIRNAME).iterdir()) == []


def test_api_rejects_pdf_over_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    response = client.post(
        "/api/purchases",
        data={
            "product_name": "Drill",
            "purchase_date": "2025-04-03",
            "purchase_type": "private",
        },
        files={
            "file": (
                "receipt.pdf",
                b"%PDF-" + b"x" * (storage.MAX_PDF_SIZE_BYTES + 1 - len(b"%PDF-")),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413


@pytest.mark.parametrize("failure", ["insert", "promote"])
def test_api_failure_leaves_no_purchase_or_pdf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    data_root = tmp_path / "profile"
    data_root.mkdir()
    monkeypatch.setenv(storage.DATA_DIR_ENV, str(data_root))
    if failure == "insert":
        def fail(*args: object, **kwargs: object) -> None:
            raise sqlite3.IntegrityError("injected insert failure")

        monkeypatch.setattr(purchases, "_insert_purchase", fail)
    else:
        def fail(staged_path: Path, document_path: Path) -> None:
            raise OSError("injected promotion failure")

        monkeypatch.setattr(purchases, "_promote_staged_file", fail)

    response = client.post(
        "/api/purchases",
        data={
            "product_name": "Drill",
            "purchase_date": "2025-04-03",
            "purchase_type": "private",
        },
        files={"file": ("receipt.pdf", _pdf(), "application/pdf")},
    )

    assert response.status_code == 500
    profile = ProfileStorage(data_root)
    with profile.connect() as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'purchase'"
        ).fetchone() is None
    assert list(profile.documents_dir.iterdir()) == []
    assert not list(profile.data_root.glob(".purchase-*.tmp"))