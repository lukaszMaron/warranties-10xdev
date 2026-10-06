# Add Purchase from PDF with Editable OCR Fields — Implementation Plan

## Overview

Implement the S-01 user flow: upload a receipt or invoice PDF, extract suggested values locally, let the owner correct them, and save the corrected purchase with its PDF. Require product name, purchase date, and purchase type; seller, payment method, and a custom warranty end date are optional.

## Current State Analysis

- `src/warranties_10xdev/__init__.py` is still a greeting-only console entry point; no FastAPI application or purchase routes exist.
- `pyproject.toml` now has FastAPI, Uvicorn, and the F-01 storage dependency, but no multipart upload parser, PDF renderer, OCR wrapper, or purchase schema.
- `src/warranties_10xdev/storage.py` provides the configured private data root, `profile.sqlite3`, `documents/`, an owner-level lock, and a 20 MiB PDF size validator. It does not yet define purchase tables or file-write methods.
- `package.json` contains only the npm package named `uv`; no Astro app or frontend source exists. The stack hand-off calls for Astro/TypeScript UI work to be done manually.
- The roadmap marks S-01 as blocked by required fields, which are now decided. F-01 is still `in-progress`, and its manual privacy/persistence check remains pending.
- The PRD requires data correction before saving and says corrections must not be lost. It expects OCR for purchase date, seller/location, and payment method; product name and purchase type are entered or corrected by the user.

## Desired End State

The owner can use the web UI to choose a PDF up to 20 MiB, review OCR suggestions, edit them, fill any missing required values manually, and explicitly save. Text PDFs and scanned PDFs are supported; OCR runs locally with Polish language data and no invoice content is sent to an external OCR provider.

The saved purchase stores the corrected field values and an opaque reference to the original PDF beneath F-01's private document root. An upload preview or cancelled form does not create a saved purchase or leave a permanent document. Search, warranty calculation, and the expiring-warranty dashboard remain later slices.

### Key Discoveries:

- F-01's storage contract and remaining manual prerequisite are recorded in `context/changes/private-purchase-storage-boundary/plan.md` and its Progress section.
- FastAPI and Uvicorn are available, but the package entry point only prints a greeting: `src/warranties_10xdev/__init__.py:1-2`.
- The current private storage boundary has a database connection, document path, lock, and PDF byte-limit helper: `src/warranties_10xdev/storage.py:15-72` and `src/warranties_10xdev/storage.py:184-189`.
- The stack hand-off identifies Astro/TypeScript as the frontend work still to be added: `10xdevs/context/foundation/tech-stack.md`.
- Official PyMuPDF docs confirm a compact local OCR API backed by Tesseract, but PyMuPDF is offered under AGPL or commercial terms. The official pypdfium2 docs describe text extraction and PDF rendering and identify Apache-2.0/BSD-3-Clause licensing for pypdfium2; pairing it with local Tesseract avoids introducing PyMuPDF's strong-copyleft dependency into a project with no declared distribution license.

## What We're NOT Doing

- Search by product name, warranty-end calculation, expiring-warranty dashboard, or reminders; these are separate roadmap slices.
- Manual-only purchase creation; it is S-02.
- Sending invoice PDFs or OCR text to a hosted OCR, AI, or other third-party service.
- Authentication, multi-user accounts, document sharing, hosting selection, or deployment automation.
- Automatic deduplication, bulk import, image uploads, or photo capture.
- Calculating a default warranty end date in this change. An optional custom warranty end date may be saved for the later warranty-logic slice.

## Implementation Approach

Use the Astro/TypeScript UI and FastAPI service as one user flow. The UI sends the selected PDF to a preview endpoint, which enforces the existing 20 MiB limit, validates that it is a readable PDF, extracts embedded text with pypdfium2, and renders image-only pages for local Tesseract OCR when needed. Configure Polish language data as the primary OCR language. Return editable suggestions without persisting a purchase or PDF. The UI retains those suggestions as ordinary form state so later user edits are never replaced by extraction results.

On explicit save, validate required fields, acquire F-01's profile lock, stage the PDF under the private data root, insert corrected values and the generated document reference in SQLite, then atomically move the PDF into `documents/`. If either side fails, roll back the database transaction and remove the staged/final file as appropriate. The PDF filename comes from a server-generated opaque ID, never the client path or supplied filename. Add only the dependencies needed for multipart upload, pypdfium2 rendering/text extraction, local Tesseract invocation, and Astro; document the Tesseract executable and Polish language-data prerequisite.

## Critical Implementation Details

OCR suggestions are returned once as an editable draft; they must not be re-applied after the user starts editing. Preview is non-persistent, while Save is the single persistence boundary for both corrected metadata and the source PDF. F-01's manual verification (Progress item 1.3) must pass before this implementation is run, because S-01 depends on its private storage and Windows/POSIX permission contract.

## Phase 1: Local PDF Upload and Editable OCR Review

### Overview

Add the minimum Astro screen and FastAPI preview route that accept a private PDF, extract local text/OCR suggestions, and expose an editable draft without saving the purchase.

### Changes Required:

#### 1. Runtime and frontend setup

**File**: `pyproject.toml`, `uv.lock`, `frontend/package.json`, `frontend/astro.config.mjs`

**Intent**: Add the dependencies and minimal frontend configuration needed for same-owner PDF preview and field correction. Preserve the existing Python console command.

**Contract**: FastAPI multipart handling accepts one PDF up to the existing 20 MiB limit. The frontend is a small Astro/TypeScript application with a reproducible production build; API origin is configuration, not a hard-coded host. pypdfium2 handles embedded text and rendering, and Tesseract is a separately installed local executable with Polish language data. Do not add external OCR/API credentials.

#### 2. Local PDF extraction service

**File**: `src/warranties_10xdev/pdf_extraction.py`

**Intent**: Convert readable text and scanned PDF pages into best-effort editable purchase suggestions while keeping the document on the local host.

**Contract**: Accept bounded PDF bytes and return suggested `product_name`, `purchase_date`, `seller`, and `payment_method` values plus extraction warnings. Use embedded text when available and OCR image-only page content locally. `purchase_type` and optional `warranty_end_date` are user-entered, not inferred from OCR. Unsupported, corrupt, encrypted, or unreadable input produces a user-correctable extraction error rather than a persisted record. Add deterministic parser tests using synthetic PDFs; never require real invoices in the test suite.

#### 3. Preview API and validation

**File**: `src/warranties_10xdev/api.py`, `src/warranties_10xdev/pdf_extraction.py`, `pyproject.toml`

**Intent**: Expose a FastAPI app and a preview endpoint that validates uploads and returns editable suggestions without writing a purchase or document.

**Contract**: `POST /api/purchases/preview` receives one multipart PDF, enforces the existing 20 MiB byte limit while reading, checks PDF signature/readability, and returns draft field values with per-field extraction warnings. Oversize or invalid PDFs return a clear client error. The route does not trust MIME type or client filename and does not expose filesystem paths. A configurable same-origin/local development setup supports the Astro UI.

#### 4. Astro upload and correction form

**File**: `frontend/src/pages/purchases/new.astro`, `frontend/src/lib/api.ts`

**Intent**: Let the owner select a PDF, see editable suggestions, fill required fields manually when OCR misses them, and continue to Save without losing corrections.

**Contract**: Require `product_name`, `purchase_date`, and `purchase_type` (`private` or `business`). `seller`, `payment_method`, and `warranty_end_date` are optional. Show a clear non-blocking extraction warning and keep the PDF selected when extraction fails so required values can be entered manually. Saving is disabled only while the preview request is pending or required fields are invalid; no value is silently overwritten after it is shown to the user.

#### 5. Extraction and route tests

**File**: `tests/test_pdf_extraction.py`, `tests/test_pdf_preview_api.py`

**Intent**: Verify local extraction behavior, safe upload validation, and manual completion when OCR is incomplete or unavailable.

**Contract**: Cover text-based PDF, scanned/image-only PDF, missing fields, malformed/encrypted input, oversized input, and extraction/runtime failure. Mock the Tesseract process boundary for deterministic tests; the unit suite must not need a local Tesseract installation or external service.

### Success Criteria:

#### Automated Verification:

- `uv run pytest tests/test_pdf_extraction.py tests/test_pdf_preview_api.py` passes for text/scanned inputs, field mapping, local OCR adapter behavior, invalid PDFs, the 20 MiB boundary, and non-persistent preview.
- `npm --prefix frontend run build` completes successfully.

#### Manual Verification:

- After F-01 manual verification passes, run the UI and API locally; preview one text-based PDF and one scanned Polish PDF, confirm the PDF is processed locally, and edit an extracted value without it being overwritten.
- Cause extraction to fail and confirm the user can still enter the required values while retaining the selected PDF for Save.

**Implementation Note**: After automated verification, pause for manual confirmation before proceeding to Phase 2.

## Phase 2: Save Corrected Purchase and Private PDF

### Overview

Persist the owner's corrected purchase fields and original PDF together through F-01's private storage boundary, with cleanup if either persistence step fails.

### Changes Required:

#### 1. Purchase persistence contract

**File**: `src/warranties_10xdev/storage.py`, `src/warranties_10xdev/purchases.py`

**Intent**: Add the minimal purchase record contract required to save the reviewed PDF flow, reusing the existing SQLite database, documents directory, and profile lock.

**Contract**: Store an opaque purchase ID, product name, purchase date, purchase type, optional seller, optional payment method, optional custom warranty end date, generated PDF reference, and creation timestamp. Do not calculate warranty status or introduce search/dashboard behavior. PDF bytes are written only after explicit Save; database values are the corrected form values, not the original OCR suggestions.

#### 2. Save API and file/database consistency

**File**: `src/warranties_10xdev/api.py`, `src/warranties_10xdev/purchases.py`, `src/warranties_10xdev/storage.py`

**Intent**: Save one reviewed purchase and its PDF without leaving a record that points to a missing file or a permanent file without a purchase record.

**Contract**: `POST /api/purchases` validates the required fields and bounded PDF, writes a staged file under the private data root, inserts the row under the F-01 lock and a SQLite transaction, then atomically moves the staged document into `documents/`. Roll back the row and clean up staged/final bytes if a step fails. Generate filenames server-side; never construct paths from user-supplied names. The response returns the saved purchase ID and corrected values, not a public document URL.

#### 3. End-to-end persistence tests

**File**: `tests/test_pdf_purchase_flow.py`

**Intent**: Verify the complete upload, correction, and save contract and its failure cleanup.

**Contract**: Test a corrected field differing from its OCR suggestion, manual completion after extraction failure, persistence after reopening the SQLite database, private document placement, invalid required fields, 20 MiB enforcement, and cleanup when database insertion or file promotion fails. Tests use temporary profile roots and synthetic PDFs only.

#### 4. User-flow integration and documentation

**File**: `frontend/src/pages/purchases/new.astro`, `frontend/src/lib/api.ts`, `docs/operations/pdf-purchase-entry.md`

**Intent**: Connect preview to explicit Save and document the local Tesseract setup needed to operate this workflow.

**Contract**: The saved confirmation identifies the purchase without exposing a local filesystem path. The runbook lists Tesseract installation, Polish language data, the configured executable/data path, the API/frontend local run commands, and the 20 MiB limit. It states that extraction is local and that OCR failure can be completed manually.

### Success Criteria:

#### Automated Verification:

- `uv run pytest tests/test_pdf_purchase_flow.py` passes for corrected-value persistence, PDF storage, validation, and cleanup behavior.
- `uv run pytest` passes the complete backend test suite.
- `npm --prefix frontend run build` completes successfully.

#### Manual Verification:

- Save a text-based PDF and a scanned Polish PDF after correcting at least one OCR value; restart the app and verify the corrected values and PDF remain in the owner's private profile.
- Try a PDF larger than 20 MiB and an invalid file; confirm both are rejected without a purchase row or retained document.

**Implementation Note**: After all automated checks pass, pause for manual confirmation before declaring the change complete.

## Testing Strategy

### Unit Tests:

- Test embedded-text extraction, image-only OCR adapter behavior, Polish language configuration, and best-effort field mapping.
- Test required/optional field validation, PDF signature/readability checks, and the inclusive 20 MiB limit.
- Test that preview does not persist a document or purchase.

### Integration Tests:

- Exercise preview, user edits, and save through the FastAPI test client with an isolated `ProfileStorage` root.
- Verify corrected values and the private PDF survive database reopen and app restart.
- Simulate database and file-promotion failures and verify cleanup leaves no inconsistent purchase/document pair.

### Manual Testing Steps:

1. Complete F-01 Progress item 1.3 and configure the local Tesseract executable plus Polish language data.
2. Preview one text-based invoice and one scanned Polish receipt; correct a suggested field and fill a missing required field manually.
3. Save each purchase, restart the app, and verify the corrected record and original PDF persist privately; test oversized and malformed files are rejected cleanly.

## Performance Considerations

Keep the existing 20 MiB upload limit. Stream request bytes to a bounded temporary file or buffer rather than trusting `Content-Length`; render/OCR pages sequentially so a multi-page scan does not retain every raster page in memory. OCR is local and may take longer than a normal API request; show a pending state in the UI and do not couple it to the PRD's three-second home/search response target.

## Migration Notes

F-01 creates the SQLite database but no purchase schema. Add the initial purchase table through an idempotent schema initializer compatible with an existing empty F-01 database. There are no existing purchase rows or PDFs to migrate. Store generated document references, not client filenames or absolute paths, so moving the configured data root does not rewrite rows.

## References

- S-01 scope, dependencies, and blocking field decision now resolved: `context/foundation/roadmap.md`
- User story, extraction fields, privacy, correction guardrail, and 20 MiB limit: `10xdevs/context/foundation/prd.md`
- F-01 storage contract and pending manual prerequisite: `context/changes/private-purchase-storage-boundary/plan.md`
- Current private storage implementation: `src/warranties_10xdev/storage.py`
- Current server entry point: `src/warranties_10xdev/__init__.py`
- Frontend hand-off: `10xdevs/context/foundation/tech-stack.md`
- PyMuPDF OCR and license terms: https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_textpage_ocr and https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright
- pypdfium2 PDF rendering/text and license notes: https://github.com/pypdfium2-team/pypdfium2

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Local PDF Upload and Editable OCR Review

#### Automated

- [x] 1.1 `uv run pytest tests/test_pdf_extraction.py tests/test_pdf_preview_api.py` passes for text/scanned inputs, field mapping, local OCR adapter behavior, invalid PDFs, the 20 MiB boundary, and non-persistent preview. — ee5b0e7
- [x] 1.2 `npm --prefix frontend run build` completes successfully. — ee5b0e7

#### Manual

- [x] 1.3 After F-01 manual verification passes, run the UI and API locally; preview one text-based PDF and one scanned Polish PDF, confirm the PDF is processed locally, and edit an extracted value without it being overwritten. — ee5b0e7
- [x] 1.4 Cause extraction to fail and confirm the user can still enter the required values while retaining the selected PDF for Save. — ee5b0e7

### Phase 2: Save Corrected Purchase and Private PDF

#### Automated

- [x] 2.1 `uv run pytest tests/test_pdf_purchase_flow.py` passes for corrected-value persistence, PDF storage, validation, and cleanup behavior. — ebc1085
- [x] 2.2 `uv run pytest` passes the complete backend test suite. — ebc1085
- [x] 2.3 `npm --prefix frontend run build` completes successfully. — ebc1085

#### Manual

- [x] 2.4 Save a text-based PDF and a scanned Polish PDF after correcting at least one OCR value; restart the app and verify the corrected values and PDF remain in the owner's private profile. — ebc1085
- [x] 2.5 Try a PDF larger than 20 MiB and an invalid file; confirm both are rejected without a purchase row or retained document. — ebc1085