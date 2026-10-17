import io
import locale
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Any, Literal

import pypdfium2 as pdfium

from warranties_10xdev.storage import MAX_PDF_SIZE_BYTES, validate_pdf_size

OCR_LANGUAGE = "pol+eng"
OCR_TIMEOUT_SECONDS = 60

DateOrder = Literal["DMY", "MDY"]


class PdfExtractionError(ValueError):
    """Raised when the uploaded bytes cannot be read as a PDF."""


@dataclass(frozen=True)
class PdfSuggestions:
    product_name: str | None
    purchase_date: str | None
    seller: str | None
    payment_method: str | None
    warnings: dict[str, str]


def extract_pdf_suggestions(
    pdf_bytes: bytes, date_order: DateOrder | None = None
) -> PdfSuggestions:
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
    return _suggest_fields(text, ocr_warnings, date_order=date_order)


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


def _suggest_fields(
    text: str, ocr_warnings: list[str], date_order: DateOrder | None = None
) -> PdfSuggestions:
    order = date_order if date_order is not None else system_date_order()
    all_labels = tuple(
        label
        for labels in _FIELD_LABELS.values()
        for label in labels
    )
    fields: dict[str, str | None] = {}
    conflicts: set[str] = set()
    for field, labels in _FIELD_LABELS.items():
        values = _label_values(text, labels, all_labels)
        if len(set(values)) > 1:
            conflicts.add(field)
            fields[field] = None
        else:
            fields[field] = values[0] if values else None
    fields["purchase_date"] = _normalize_date(fields["purchase_date"], order)
    ocr_prefix = f"{'; '.join(ocr_warnings)} " if ocr_warnings else ""
    warnings = {
        field: ocr_prefix
        + (
            f"Multiple different {field.replace('_', ' ')} values were found; "
            "enter it manually."
            if field in conflicts
            else f"No {field.replace('_', ' ')} suggestion was found; enter it manually."
        )
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


# A separator is ":" or a "-" set off by whitespace, so "Product-ID" is not a label.
_SEPARATOR = r"(?:\s*:|\s+-(?=\s|$))"


def _label_values(
    text: str, labels: tuple[str, ...], all_labels: tuple[str, ...]
) -> list[str]:
    """Values for the most specific label level found; multi-word labels beat single words."""
    specific = tuple(label for label in labels if " " in label)
    generic = tuple(label for label in labels if " " not in label)
    for level in (specific, generic):
        values = _values_for_labels(text, level, all_labels) if level else []
        if values:
            return values
    return []


def _values_for_labels(
    text: str, labels: tuple[str, ...], all_labels: tuple[str, ...]
) -> list[str]:
    alternatives = "|".join(re.escape(label) for label in sorted(labels, key=len, reverse=True))
    next_field = "|".join(
        re.escape(label) for label in sorted(all_labels, key=len, reverse=True)
    )
    pattern = re.compile(
        rf"(?<!\S)(?:{alternatives}){_SEPARATOR}\s*(.*?)"
        rf"(?=\s+(?:{next_field}){_SEPARATOR}|\s*$)",
        re.IGNORECASE,
    )
    values: list[str] = []
    for line in text.splitlines():
        for match in pattern.finditer(line):
            value = match.group(1).strip()
            if value:
                values.append(value)
    return values


_DATE_PATTERN = re.compile(
    r"\b(?:(?P<iso_y>\d{4})-(?P<iso_m>\d{1,2})-(?P<iso_d>\d{1,2})"
    r"|(?P<sl_d>\d{1,2})/(?P<sl_m>\d{1,2})/(?P<sl_y>\d{4}|\d{2})"
    r"|(?P<a>\d{1,2})(?P<sep>[.-])(?P<b>\d{1,2})(?P=sep)(?P<y>\d{4}|\d{2}))\b"
)


def _normalize_date(value: str | None, date_order: DateOrder = "DMY") -> str | None:
    if value is None:
        return None
    for match in _DATE_PATTERN.finditer(value):
        if match["iso_y"]:
            year, month, day = match["iso_y"], match["iso_m"], match["iso_d"]
        elif match["sl_y"]:
            year, month, day = match["sl_y"], match["sl_m"], match["sl_d"]
        else:
            year = match["y"]
            day, month = (
                (match["a"], match["b"]) if date_order == "DMY" else (match["b"], match["a"])
            )
        try:
            return date(_full_year(year), int(month), int(day)).isoformat()
        except ValueError:
            continue
    return None


def _full_year(year: str) -> int:
    if len(year) == 4:
        return int(year)
    short = int(year)
    # Same pivot as strptime's %y.
    return 2000 + short if short < 69 else 1900 + short


def _date_order_from_sample(sample: str) -> DateOrder:
    """Order of day and month in a locale rendering of 2026-03-05; DMY when unclear."""
    match = re.match(r"\s*(\d{1,2})\D+(\d{1,2})\D+\d{2,4}\s*$", sample)
    if match and (int(match[1]), int(match[2])) == (3, 5):
        return "MDY"
    return "DMY"


@lru_cache(maxsize=1)
def system_date_order() -> DateOrder:
    """Day/month order of the server's system locale, read once per process."""
    try:
        previous = locale.setlocale(locale.LC_TIME)
        try:
            locale.setlocale(locale.LC_TIME, "")
            sample = date(2026, 3, 5).strftime("%x")
        finally:
            locale.setlocale(locale.LC_TIME, previous)
    except (locale.Error, ValueError):
        return "DMY"
    return _date_order_from_sample(sample)
