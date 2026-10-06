import io
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pypdfium2 as pdfium

from warranties_10xdev.storage import MAX_PDF_SIZE_BYTES, validate_pdf_size

OCR_LANGUAGE = "pol+eng"
OCR_TIMEOUT_SECONDS = 60


class PdfExtractionError(ValueError):
    """Raised when the uploaded bytes cannot be read as a PDF."""


@dataclass(frozen=True)
class PdfSuggestions:
    product_name: str | None
    purchase_date: str | None
    seller: str | None
    payment_method: str | None
    warnings: dict[str, str]


def extract_pdf_suggestions(pdf_bytes: bytes) -> PdfSuggestions:
    if len(pdf_bytes) > MAX_PDF_SIZE_BYTES:
        raise PdfExtractionError("PDF must be 20 MiB or smaller.")
    if not pdf_bytes.startswith(b"%PDF-"):
        raise PdfExtractionError("The uploaded file is not a PDF document.")
    try:
        document = pdfium.PdfDocument(pdf_bytes)
        page_count = len(document)
        if page_count == 0:
            raise PdfExtractionError("The PDF does not contain any readable pages.")
        extracted_pages = [_extract_page_text(document[index]) for index in range(page_count)]
    except PdfExtractionError:
        raise
    except Exception as exc:
        raise PdfExtractionError(
            "The PDF is corrupt, encrypted, or could not be read."
        ) from exc

    text = "\n".join(page_text for page_text, _ in extracted_pages)
    ocr_warnings = [warning for _, warning in extracted_pages if warning]
    return _suggest_fields(text, ocr_warnings)


def _extract_page_text(page: Any) -> tuple[str, str | None]:
    text_page = page.get_textpage()
    text = text_page.get_text_range().strip()
    if text:
        return text, None
    try:
        image = page.render(scale=2).to_pil()
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        return _run_tesseract(image_bytes.getvalue()), None
    except _OcrUnavailable as exc:
        return "", str(exc)
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        return "", f"Local OCR could not process this PDF page: {exc}"


class _OcrUnavailable(Exception):
    pass


def _run_tesseract(image_bytes: bytes) -> str:
    configured_command = os.environ.get("TESSERACT_CMD", "tesseract")
    executable = shutil.which(configured_command)
    if executable is None:
        raise _OcrUnavailable(
            "Local OCR is unavailable; install Tesseract with Polish language data."
        )
    command = [executable, "stdin", "stdout", "-l", OCR_LANGUAGE]
    tessdata_dir = os.environ.get("TESSDATA_PREFIX")
    if tessdata_dir:
        command.extend(["--tessdata-dir", tessdata_dir])
    try:
        result = subprocess.run(
            command,
            input=image_bytes,
            capture_output=True,
            check=False,
            timeout=OCR_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise _OcrUnavailable("Local OCR could not process this PDF page.") from exc
    if result.returncode != 0:
        raise _OcrUnavailable("Local OCR could not process this PDF page.")
    return result.stdout.decode("utf-8", errors="replace").strip()


def _suggest_fields(text: str, ocr_warnings: list[str]) -> PdfSuggestions:
    all_labels = tuple(
        label
        for labels in _FIELD_LABELS.values()
        for label in labels
    )
    product_name = _label_value(
        text, _FIELD_LABELS["product_name"], all_labels
    )
    raw_date = _label_value(
        text, _FIELD_LABELS["purchase_date"], all_labels
    )
    seller = _label_value(text, _FIELD_LABELS["seller"], all_labels)
    payment_method = _label_value(text, _FIELD_LABELS["payment_method"], all_labels)
    purchase_date = _normalize_date(raw_date)
    fields = {
        "product_name": product_name,
        "purchase_date": purchase_date,
        "seller": seller,
        "payment_method": payment_method,
    }
    warnings = {
        field: (
            f"{'; '.join(ocr_warnings)} "
            if ocr_warnings
            else ""
        ) + f"No {field.replace('_', ' ')} suggestion was found; enter it manually."
        for field, value in fields.items()
        if value is None
    }
    return PdfSuggestions(**fields, warnings=warnings)


_FIELD_LABELS = {
    "product_name": ("product name", "nazwa produktu", "product", "produkt", "item", "towar"),
    "purchase_date": (
        "purchase date", "date of purchase", "data zakupu", "data sprzedaży",
        "data sprzedazy", "date", "data",
    ),
    "seller": ("seller", "sprzedawca", "vendor", "merchant", "store", "sklep"),
    "payment_method": (
        "payment method", "metoda płatności", "metoda platnosci",
        "sposób płatności", "sposob platnosci", "payment",
    ),
}


def _label_value(
    text: str, labels: tuple[str, ...], all_labels: tuple[str, ...]
) -> str | None:
    alternatives = "|".join(re.escape(label) for label in sorted(labels, key=len, reverse=True))
    next_field = "|".join(
        re.escape(label) for label in sorted(all_labels, key=len, reverse=True)
    )
    pattern = re.compile(
        rf"(?<!\S)(?:{alternatives})\s*[:\-]\s*(.+?)"
        rf"(?=\s+(?:{next_field})\s*[:\-]|$)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _normalize_date(value: str | None) -> str | None:
    if value is None:
        return None
    candidates = re.findall(r"\b(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b", value)
    for candidate in candidates:
        for date_format in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%y", "%d/%m/%y"):
            try:
                return datetime.strptime(candidate, date_format).date().isoformat()
            except ValueError:
                continue
    return None