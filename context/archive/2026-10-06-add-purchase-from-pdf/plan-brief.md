# Add Purchase from PDF with Editable OCR Fields — Plan Brief

> Full plan: `context/changes/add-purchase-from-pdf/plan.md`

## What & Why

This change implements the PDF path in the primary user story: choose a receipt or invoice, review and correct extracted values, and save the corrected purchase with the original PDF. OCR runs locally, and if it misses required values the owner can complete them manually.

## Starting Point

F-01 now provides a private data root, SQLite connection, document directory, file-size check, and profile lock, but its manual privacy/persistence verification is still pending. The repository has no API routes, Astro app, purchase schema, or OCR integration.

## Desired End State

The owner can preview both text-based and scanned PDFs up to 20 MiB in the web UI. Product name, purchase date, and purchase type are required; seller, payment method, and a custom warranty end date are optional. OCR suggestions are editable and never replace corrections.

Only explicit Save persists the corrected values and original PDF to the private profile. OCR stays on the host, using local Tesseract with Polish language data; preview failures remain manually completable.

## Key Decisions Made

| Decision | Choice | Why |
| -------- | ------ | --- |
| Required fields | Product name, purchase date, purchase type | Product name supports later search; date and type support the PRD's later warranty calculation. |
| Optional fields | Seller, payment method, custom warranty end date | OCR may not find them reliably, and a custom end date is not needed for every purchase. |
| OCR privacy | Local processing only | Preserves the PRD's owner-only invoice-data boundary without sending documents to a third party. |
| PDF support | Text-based and scanned PDFs | Supports digital invoices and scans of paper receipts. |
| OCR failure | Allow manual completion | A missed field should not prevent the owner from using the review-and-save flow. |
| OCR engine | pypdfium2 plus local Tesseract | Extracts/renders PDFs with a permissively licensed wrapper and performs OCR without PyMuPDF's AGPL/commercial licensing choice. |

## Scope

**In scope:** Astro upload/review screen, FastAPI preview/save endpoints, local PDF text/OCR extraction, editable fields, initial purchase persistence, private PDF storage, validation, tests, and Tesseract setup notes.

**Out of scope:** manual-only purchase entry, search, warranty calculations, expiring-warranty dashboard, reminders, accounts, hosted OCR, image uploads, and deployment automation.

## Architecture / Approach

Astro sends a bounded PDF to FastAPI for local text extraction or Tesseract OCR. The preview response is a non-persistent editable draft. On explicit Save, FastAPI validates required values and persists the corrected row and generated PDF reference through F-01's SQLite, private directory, and lock contract; failed saves clean up staged files.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| ----- | ---------------- | -------- |
| 1. Local PDF Upload and Editable OCR Review | Astro form and FastAPI preview with local extraction for text and scanned PDFs. | Tesseract and Polish language data must be installed on the host. |
| 2. Save Corrected Purchase and Private PDF | Corrected fields and original PDF persist together in the private profile. | Filesystem and SQLite writes need explicit failure cleanup. |

**Prerequisites:** F-01's manual privacy/persistence check passes; local Tesseract and Polish language data are available; `WARRANTIES_DATA_DIR` is configured.
**Estimated effort:** Two implementation phases; no calendar estimate.

## Open Risks & Assumptions

- Receipt layouts vary; OCR remains best-effort and the user correction step is authoritative.
- This change stores an optional custom warranty end date but does not calculate default warranty dates or status.
- pypdfium2's bundled PDFium license notices must be retained with any distributed binary; confirm the exact wheel's bundled notices during implementation.
- F-01 is currently in progress. Implementation must wait for its pending manual verification and completion.

## Success Criteria (Summary)

- The owner can preview and edit extracted values from text-based and scanned PDFs without sending invoice content to an external provider.
- The owner can save required fields and the PDF, including manual completion after OCR failure; corrections remain unchanged.
- Saved values and the PDF survive restart in the owner's private profile, while invalid or oversized files leave no saved data.