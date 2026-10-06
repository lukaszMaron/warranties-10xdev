from dataclasses import asdict

from fastapi import FastAPI, File, HTTPException, UploadFile

from warranties_10xdev.pdf_extraction import PdfExtractionError, extract_pdf_suggestions
from warranties_10xdev.storage import MAX_PDF_SIZE_BYTES

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