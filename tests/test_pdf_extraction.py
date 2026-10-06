import subprocess

import pytest

from warranties_10xdev import pdf_extraction
from warranties_10xdev.pdf_extraction import PdfExtractionError, extract_pdf_suggestions


def _pdf(content: bytes) -> bytes:
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
    output.extend(f"xref\n0 {len(offsets)}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    )
    return bytes(output)


def test_extracts_fields_from_embedded_text_pdf() -> None:
    content = (
        b"BT /F1 12 Tf 72 720 Td (Product: Cordless drill) Tj T* "
        b"(Purchase date: 2025-04-03) Tj T* (Seller: Tool shop) Tj T* "
        b"(Payment method: Card) Tj ET"
    )

    result = extract_pdf_suggestions(_pdf(content))

    assert result.product_name == "Cordless drill"
    assert result.purchase_date == "2025-04-03"
    assert result.seller == "Tool shop"
    assert result.payment_method == "Card"
    assert result.warnings == {}


def test_ocr_uses_polish_language_and_returns_editable_suggestions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def mock_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        assert kwargs["input"].startswith(b"\x89PNG")
        return subprocess.CompletedProcess(command, 0, stdout=b"Produkt: Wiertarka\nData zakupu: 03.04.2025\n", stderr=b"")

    monkeypatch.setattr(pdf_extraction.shutil, "which", lambda command: "tesseract.exe")
    monkeypatch.setattr(pdf_extraction.subprocess, "run", mock_run)

    result = extract_pdf_suggestions(_pdf(b""))

    assert calls[0][-2:] == ["-l", "pol+eng"]
    assert result.product_name == "Wiertarka"
    assert result.purchase_date == "2025-04-03"
    assert "seller" in result.warnings
    assert "payment_method" in result.warnings


def test_missing_fields_are_returned_with_manual_entry_warnings() -> None:
    result = extract_pdf_suggestions(_pdf(b"BT /F1 12 Tf 72 720 Td (Unlabelled text) Tj ET"))

    assert result.product_name is None
    assert result.purchase_date is None
    assert set(result.warnings) == {
        "product_name",
        "purchase_date",
        "seller",
        "payment_method",
    }


@pytest.mark.parametrize("pdf_bytes", [b"not a PDF", b"%PDF-1.4\ntruncated"])
def test_rejects_malformed_pdf(pdf_bytes: bytes) -> None:
    with pytest.raises(PdfExtractionError):
        extract_pdf_suggestions(pdf_bytes)


def test_rejects_encrypted_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    class EncryptedDocument:
        def __init__(self, pdf_bytes: bytes) -> None:
            raise RuntimeError("password required")

    monkeypatch.setattr(pdf_extraction.pdfium, "PdfDocument", EncryptedDocument)

    with pytest.raises(PdfExtractionError, match="encrypted"):
        extract_pdf_suggestions(b"%PDF-1.4\nvalid-looking-header")


def test_reports_missing_tesseract_as_field_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pdf_extraction.shutil, "which", lambda command: None)

    result = extract_pdf_suggestions(_pdf(b""))

    assert set(result.warnings) == {
        "product_name",
        "purchase_date",
        "seller",
        "payment_method",
    }
    assert all("Tesseract" in warning for warning in result.warnings.values())


def test_rejects_oversized_pdf() -> None:
    with pytest.raises(PdfExtractionError, match="20 MiB"):
        extract_pdf_suggestions(b"%PDF-" + b"x" * (20 * 1024 * 1024))