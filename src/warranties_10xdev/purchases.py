import os
import sqlite3
import tempfile
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import pypdfium2 as pdfium

from warranties_10xdev.storage import (
    MAX_PDF_SIZE_BYTES,
    ProfileStorage,
    validate_pdf_size,
)


class PurchaseValidationError(ValueError):
    """Raised when a purchase or its PDF does not meet the save contract."""


class PurchaseSaveError(RuntimeError):
    """Raised when purchase metadata and its PDF could not be saved together."""


@dataclass(frozen=True)
class PurchaseInput:
    product_name: str
    purchase_date: date
    purchase_type: str
    seller: str | None = None
    payment_method: str | None = None
    warranty_end_date: date | None = None


@dataclass(frozen=True)
class SavedPurchase:
    purchase_id: str
    product_name: str
    purchase_date: str
    purchase_type: str
    seller: str | None
    payment_method: str | None
    warranty_end_date: str | None
    document_ref: str
    created_at: str


def save_purchase(
    profile: ProfileStorage, purchase: PurchaseInput, pdf_bytes: bytes
) -> SavedPurchase:
    normalized = _validate_purchase(purchase)
    _validate_pdf(pdf_bytes)

    with profile.lock:
        purchase_id = uuid.uuid4().hex
        document_ref = f"{purchase_id}.pdf"
        staged_path: Path | None = None
        document_path = profile.documents_dir / document_ref
        connection: sqlite3.Connection | None = None
        created_at = datetime.now(timezone.utc).isoformat()
        try:
            staged_path = _stage_pdf(profile, pdf_bytes)
            connection = profile.connect()
            connection.execute("BEGIN IMMEDIATE")
            _create_purchase_schema(connection)
            _insert_purchase(connection, purchase_id, document_ref, normalized, created_at)
            _promote_staged_file(staged_path, document_path)
            staged_path = None
            connection.commit()
        except Exception as exc:
            if connection is not None:
                try:
                    connection.rollback()
                except sqlite3.Error:
                    pass
            _remove_file(staged_path)
            _remove_file(document_path)
            raise PurchaseSaveError(
                "The purchase and its PDF could not be saved together."
            ) from exc
        finally:
            if connection is not None:
                connection.close()

    return SavedPurchase(
        purchase_id=purchase_id,
        product_name=normalized.product_name,
        purchase_date=normalized.purchase_date.isoformat(),
        purchase_type=normalized.purchase_type,
        seller=normalized.seller,
        payment_method=normalized.payment_method,
        warranty_end_date=(
            normalized.warranty_end_date.isoformat()
            if normalized.warranty_end_date is not None
            else None
        ),
        document_ref=document_ref,
        created_at=created_at,
    )


def _validate_purchase(purchase: PurchaseInput) -> PurchaseInput:
    if not isinstance(purchase.product_name, str) or not purchase.product_name.strip():
        raise PurchaseValidationError("Product name is required.")
    if not isinstance(purchase.purchase_date, date):
        raise PurchaseValidationError("Purchase date is required.")
    if purchase.purchase_type not in {"private", "business"}:
        raise PurchaseValidationError("Purchase type must be private or business.")
    optional_values: dict[str, str | None] = {}
    for field_name in ("seller", "payment_method"):
        value = getattr(purchase, field_name)
        if value is not None and not isinstance(value, str):
            raise PurchaseValidationError(f"{field_name.replace('_', ' ').title()} must be text.")
        optional_values[field_name] = value.strip() or None if value is not None else None
    if purchase.warranty_end_date is not None and not isinstance(
        purchase.warranty_end_date, date
    ):
        raise PurchaseValidationError("Warranty end date must be a valid date.")
    return PurchaseInput(
        product_name=purchase.product_name.strip(),
        purchase_date=purchase.purchase_date,
        purchase_type=purchase.purchase_type,
        seller=optional_values["seller"],
        payment_method=optional_values["payment_method"],
        warranty_end_date=purchase.warranty_end_date,
    )


def _validate_pdf(pdf_bytes: bytes) -> None:
    if not isinstance(pdf_bytes, bytes):
        raise PurchaseValidationError("PDF content must be bytes.")
    try:
        validate_pdf_size(len(pdf_bytes))
    except ValueError as exc:
        raise PurchaseValidationError(str(exc)) from exc
    if not pdf_bytes.startswith(b"%PDF-"):
        raise PurchaseValidationError("The uploaded file is not a PDF document.")
    try:
        document = pdfium.PdfDocument(pdf_bytes)
        if len(document) == 0:
            raise PurchaseValidationError("The PDF does not contain any readable pages.")
    except PurchaseValidationError:
        raise
    except Exception as exc:
        raise PurchaseValidationError("The PDF is corrupt, encrypted, or unreadable.") from exc


def _stage_pdf(profile: ProfileStorage, pdf_bytes: bytes) -> Path:
    with tempfile.NamedTemporaryFile(
        mode="wb", prefix=".purchase-", suffix=".tmp", dir=profile.data_root, delete=False
    ) as staged_file:
        staged_file.write(pdf_bytes)
        staged_file.flush()
        os.fsync(staged_file.fileno())
        staged_path = Path(staged_file.name)
    profile._restrict_permissions(staged_path, is_directory=False)
    return staged_path


def _create_purchase_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS purchase (
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


def _insert_purchase(
    connection: sqlite3.Connection,
    purchase_id: str,
    document_ref: str,
    purchase: PurchaseInput,
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO purchase (
            purchase_id, product_name, purchase_date, purchase_type, seller,
            payment_method, warranty_end_date, document_ref, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            purchase_id,
            purchase.product_name,
            purchase.purchase_date.isoformat(),
            purchase.purchase_type,
            purchase.seller,
            purchase.payment_method,
            purchase.warranty_end_date.isoformat()
            if purchase.warranty_end_date is not None
            else None,
            document_ref,
            created_at,
        ),
    )


def _promote_staged_file(staged_path: Path, document_path: Path) -> None:
    os.replace(staged_path, document_path)


def _remove_file(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass