from dataclasses import asdict
from datetime import date
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from warranties_10xdev.pdf_extraction import PdfExtractionError, extract_pdf_suggestions
from warranties_10xdev.purchases import (
    PurchaseInput,
    PurchaseSaveError,
    PurchaseValidationError,
    save_purchase as persist_purchase,
)
from warranties_10xdev.storage import (
    MAX_PDF_SIZE_BYTES,
    ProfileStorage,
    StorageConfigurationError,
)

UPLOAD_CHUNK_SIZE = 64 * 1024

app = FastAPI(title="PamiętajGwarancje API")


async def _read_bounded_upload(upload: UploadFile) -> bytes:
    contents = bytearray()
    while True:
        remaining = MAX_PDF_SIZE_BYTES + 1 - len(contents)
        chunk = await upload.read(min(UPLOAD_CHUNK_SIZE, remaining))
        if not chunk:
            break
        contents.extend(chunk)
        if len(contents) > MAX_PDF_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="PDF must be 20 MiB or smaller.")
    return bytes(contents)


@app.post("/api/purchases/preview")
async def preview_purchase(file: UploadFile = File(...)) -> dict[str, object]:
    pdf_bytes = await _read_bounded_upload(file)
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="The uploaded file is not a PDF document.")
    try:
        suggestions = extract_pdf_suggestions(pdf_bytes)
    except PdfExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return asdict(suggestions)


@app.post("/api/purchases")
async def save_purchase(
    file: UploadFile = File(...),
    product_name: str = Form(...),
    purchase_date: date = Form(...),
    purchase_type: Literal["private", "business"] = Form(...),
    seller: str | None = Form(None),
    payment_method: str | None = Form(None),
    warranty_end_date: date | None = Form(None),
) -> dict[str, str | None]:
    pdf_bytes = await _read_bounded_upload(file)
    try:
        profile = ProfileStorage.from_environment()
        saved = persist_purchase(
            profile,
            PurchaseInput(
                product_name=product_name,
                purchase_date=purchase_date,
                purchase_type=purchase_type,
                seller=seller,
                payment_method=payment_method,
                warranty_end_date=warranty_end_date,
            ),
            pdf_bytes,
        )
    except PurchaseValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except StorageConfigurationError as exc:
        raise HTTPException(
            status_code=503, detail="Private profile storage is unavailable."
        ) from exc
    except PurchaseSaveError as exc:
        raise HTTPException(
            status_code=500,
            detail="The purchase and its PDF could not be saved together.",
        ) from exc
    return asdict(saved)