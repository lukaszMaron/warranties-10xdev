from fastapi.testclient import TestClient

from warranties_10xdev import api
from warranties_10xdev.pdf_extraction import PdfExtractionError, PdfSuggestions
from warranties_10xdev.storage import MAX_PDF_SIZE_BYTES

client = TestClient(api.app)


def test_preview_returns_suggestions_without_persisting_upload(
    monkeypatch, tmp_path
) -> None:
    data_root = tmp_path / "profile"
    data_root.mkdir()
    monkeypatch.setenv("WARRANTIES_DATA_DIR", str(data_root))
    monkeypatch.setattr(
        api,
        "extract_pdf_suggestions",
        lambda pdf_bytes: PdfSuggestions(
            product_name="Drill",
            purchase_date="2025-04-03",
            seller=None,
            payment_method=None,
            warnings={"seller": "Enter manually", "payment_method": "Enter manually"},
        ),
    )

    response = client.post(
        "/api/purchases/preview",
        files={"file": ("../../private.pdf", b"%PDF-contents", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "product_name": "Drill",
        "purchase_date": "2025-04-03",
        "seller": None,
        "payment_method": None,
        "warnings": {"seller": "Enter manually", "payment_method": "Enter manually"},
    }
    assert list(data_root.iterdir()) == []


def test_preview_rejects_non_pdf_signature() -> None:
    response = client.post(
        "/api/purchases/preview",
        files={"file": ("invoice.pdf", b"not a PDF", "application/pdf")},
    )

    assert response.status_code == 422
    assert "not a PDF" in response.json()["detail"]


def test_preview_rejects_corrupt_pdf_with_clear_client_error(monkeypatch) -> None:
    def reject_pdf(pdf_bytes: bytes) -> None:
        raise PdfExtractionError("The PDF is corrupt, encrypted, or could not be read.")

    monkeypatch.setattr(api, "extract_pdf_suggestions", reject_pdf)

    response = client.post(
        "/api/purchases/preview",
        files={"file": ("invoice.pdf", b"%PDF-corrupt", "application/pdf")},
    )

    assert response.status_code == 422
    assert "corrupt" in response.json()["detail"]


def test_preview_accepts_exact_size_limit(monkeypatch) -> None:
    monkeypatch.setattr(
        api,
        "extract_pdf_suggestions",
        lambda pdf_bytes: PdfSuggestions(None, None, None, None, {}),
    )

    response = client.post(
        "/api/purchases/preview",
        files={
            "file": (
                "invoice.pdf",
                b"%PDF-" + b"x" * (MAX_PDF_SIZE_BYTES - len(b"%PDF-")),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200


def test_preview_rejects_upload_over_size_limit() -> None:
    response = client.post(
        "/api/purchases/preview",
        files={
            "file": (
                "invoice.pdf",
                b"%PDF-" + b"x" * (MAX_PDF_SIZE_BYTES + 1 - len(b"%PDF-")),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413
    assert "20 MiB" in response.json()["detail"]