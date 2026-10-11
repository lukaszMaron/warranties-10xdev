# Add Purchase Manually Implementation Plan

## Overview

Add a manual purchase path that saves purchase details without requiring a PDF and immediately shows an effective warranty end date and status. Preserve the existing PDF-assisted path, clearly label PRD-derived dates as estimates, and retain any user-entered end date as the override.

## Current State Analysis

- `PurchaseInput` and `_validate_purchase` already represent and validate purchase metadata independently of OCR suggestions ([purchases.py:22-31,106-132](../../../src/warranties_10xdev/purchases.py#L22-L31)).
- The current `POST /api/purchases` route requires a PDF, and `save_purchase` validates and atomically stores the PDF with the purchase ([api.py:51-77](../../../src/warranties_10xdev/api.py#L51-L77), [purchases.py:49-77](../../../src/warranties_10xdev/purchases.py#L49-L77)).
- The purchase table has `document_ref TEXT NOT NULL UNIQUE`; the response type also treats that field as non-null. S-02 therefore needs an explicit no-document representation and a migration for existing S-01 profiles ([purchases.py:161-173](../../../src/warranties_10xdev/purchases.py#L161-L173), [api.ts:15-25](../../../frontend/src/lib/api.ts#L15-L25)).
- The current page's save gate requires a selected file. Its two-mode UI must leave PDF preview and correction intact while allowing a manual submission without preview ([new.astro:133-150,233-244](../../../frontend/src/pages/purchases/new.astro#L133-L150)).
- The PRD specifies a private/business date formula and an override; the active roadmap promises a calculated status and end date. The research artifact records the UOKiK distinction between actual commercial guarantee terms and statutory seller responsibility ([PRD:83-87](../../../10xdevs/context/foundation/prd.md#L83-L87), [roadmap:94-103](../../../context/foundation/roadmap.md#L94-L103), [research.md](research.md)).

## Desired End State

The owner can select either PDF-assisted or manual entry on the existing purchase page. Both paths save through the same purchase contract; the PDF is optional, and a missing document is represented as `null`, never by a placeholder file. The saved response provides the entered override, effective warranty end date, date basis, and status so the UI can distinguish an estimate from a user-provided date.

When no override is entered, use the PRD rule as an estimate: two calendar years from the purchase date for `private`, one calendar year for `business`. A February 29 anniversary falls on February 28 when the target year is not a leap year. A supplied end date overrides the estimate. The purchase remains active through its end date and becomes expired the following day; when no effective date can be established, its status is unknown. “Expiring soon” remains S-06 scope.

### Key Discoveries:

- The S-01 persistence path already supplies the private profile lock and PDF/database rollback behavior to preserve when a PDF is provided ([purchases.py:49-77](../../../src/warranties_10xdev/purchases.py#L49-L77)).
- The current schema is created with `CREATE TABLE IF NOT EXISTS`; the inspected source has no existing migration path, so a schema declaration change alone is insufficient for an existing profile ([purchases.py:161-173](../../../src/warranties_10xdev/purchases.py#L161-L173), [research.md](research.md)).
- The archived S-01 plan specifies product name, purchase date, and purchase type as required fields, but the current PRD and S-02 roadmap still list the required-field decision as open. This plan records the user's confirmation of that field set; the PRD, roadmap details, and active change note must be brought into agreement ([S-01 plan](../../../context/archive/2026-10-06-add-purchase-from-pdf/plan.md#L83-L87), [PRD:103](../../../10xdevs/context/foundation/prd.md#L103), [roadmap:102-103](../../../context/foundation/roadmap.md#L102-L103)).
- The PRD formula is an application estimate, not a complete model of a guarantor's terms or statutory rights. The UI and response must identify whether the effective date is estimated or user-entered ([UOKiK: Gwarancja](https://prawakonsumenta.uokik.gov.pl/reklamacja/gwarancja/), [research.md](research.md)).

## What We're NOT Doing

- No OCR, upload, or fabricated document for manual-only entry.
- No tracking of statutory seller responsibility as a commercial guarantee, or modeling of guarantee extensions after repairs or replacements.
- No “expiring soon” threshold, dashboard, search, edit, delete, reminders, or changes to the S-06 scope.
- No new account, sharing, or access-control model; keep F-01's private local profile boundary.

## Implementation Approach

Keep the existing purchase record and `POST /api/purchases` route, making the upload optional rather than creating a second purchase contract. Migrate `document_ref` to nullable while preserving all existing purchase rows and PDF references. Keep `warranty_end_date` as the explicitly entered override; derive the effective date, its basis (`user`, `estimate`, or `unknown`), and the status from the purchase fields and current local calendar date instead of persisting duplicate computed values. Add a clearly separated manual mode to the existing page, and update the PRD, roadmap details, and change notes to reflect the decisions made during planning.

## Critical Implementation Details

The SQLite migration must preserve existing S-01 rows and document references, and must be safe when profile initialization runs again. When an upload is present, retain the current staged-file and database rollback guarantees; when absent, commit only the purchase row. Keep the stored override distinct from the derived effective date so estimate calculations do not overwrite the source value.

## Phase 1: Optional-Document Persistence and Warranty Rules

### Overview

Extend purchase persistence to support a purchase without a document, migrate existing profiles without losing S-01 data, and implement the agreed date/status calculation as a deterministic domain operation.

### Changes Required:

#### 1. Purchase schema and persistence

**File**: `src/warranties_10xdev/purchases.py`, `tests/test_pdf_purchase_flow.py`

**Intent**: Allow the existing purchase record to exist without an attached PDF while preserving the current PDF-backed save behavior and private profile lock.

**Contract**: Make `document_ref` nullable and allow the persistence operation to receive no PDF. Add an idempotent SQLite migration for existing profiles that preserves purchase values, unique non-null document references, and the corresponding PDF files. Do not create placeholder PDFs. A supplied PDF continues through the existing staged-file/transaction path; a missing PDF creates only the database row.

#### 2. Warranty date and status calculation

**File**: `src/warranties_10xdev/purchases.py`, `tests/test_warranty_calculation.py`

**Intent**: Calculate the effective warranty date and current status from the recorded purchase data without replacing the stored user override.

**Contract**: Require `product_name`, `purchase_date`, and `purchase_type`; keep `seller`, `payment_method`, and the explicit `warranty_end_date` optional. Use two calendar years for `private` and one for `business`, with February 29 clamped to February 28 in a non-leap target year. An explicit end date overrides the estimate. Return the effective date, its basis (`user`, `estimate`, or `unknown`), and status (`active`, `expired`, or `unknown`). Compare using the local calendar date; a date is active through the stated end date and expired afterward. Accept the current date as a calculation input for deterministic tests. Do not add an “expiring soon” state.

### Success Criteria:

#### Automated Verification:

- `uv run pytest tests/test_pdf_purchase_flow.py tests/test_warranty_calculation.py` passes for manual-only persistence, migration preservation of existing records and document references, existing PDF atomic-save behavior, private/business estimates, user override, February 29, inclusive end-date status, and unknown status when no effective date exists.

#### Manual Verification:

- On a copy of a profile containing an S-01 purchase, run the migration and confirm the existing purchase data and PDF remain readable and the profile can also store a row without a document reference.

**Implementation Note**: After completing this phase and its automated verification, pause for human confirmation that the migration check passed before proceeding to Phase 2.

## Phase 2: Shared API and Two-Mode Entry Page

### Overview

Connect the document-optional persistence and warranty result to the existing purchase API and page, while keeping the PDF-assisted flow available as a separate, explicit mode.

### Changes Required:

#### 1. Purchase API and response contract

**File**: `src/warranties_10xdev/api.py`, `src/warranties_10xdev/purchases.py`, `frontend/src/lib/api.ts`, `tests/test_pdf_purchase_flow.py`

**Intent**: Accept both manual and PDF-assisted submissions through the existing purchase resource and return the computed warranty result needed by the UI.

**Contract**: Make the multipart PDF field optional on `POST /api/purchases`; continue bounded upload and PDF validation when a file is supplied. Preserve `warranty_end_date` as the entered override in storage and in its existing response field. Add response fields for effective end date, date basis, and status; type `document_ref` as nullable. Invalid required fields and invalid supplied PDFs retain client-error responses, and private storage failures retain the current error boundary.

#### 2. Manual and PDF-assisted UI modes

**File**: `frontend/src/pages/purchases/new.astro`, `frontend/src/lib/api.ts`

**Intent**: Let the owner choose manual entry or PDF-assisted entry without making OCR or a PDF prerequisite for a manual purchase.

**Contract**: Add two explicit modes on the existing page. Manual mode does not require a file or call preview; PDF mode retains file selection, preview, editable suggestions, and explicit save. Both modes require product name, purchase date, and purchase type. Show the effective end date and status after saving, visibly label an estimate as estimated, and let a supplied end date override the estimate. Keep field values and the selected PDF stable through preview errors and preserve the existing PDF save flow.

#### 3. Product-decision documentation

**File**: `10xdevs/context/foundation/prd.md`, `context/foundation/roadmap.md`, `context/changes/add-purchase-manually/change.md`

**Intent**: Record the decisions confirmed during planning and remove stale statements that still mark required fields as unresolved.

**Contract**: Document the required/optional fields, date estimate and override, end-date inclusivity, February 29 rule, and unknown status. Remove the resolved required-fields question from the PRD and S-01/S-02 roadmap details while preserving the separate S-06 “soon expiring” question. Update the active change note that currently says the required-fields decision is open. Do not change lifecycle metadata outside the planning/implementation skills.

### Success Criteria:

#### Automated Verification:

- `uv run pytest` passes the backend suite, including manual no-PDF requests, nullable document responses, warranty results, migration preservation, and the existing PDF correction/save flow.
- `npm --prefix frontend run build` completes successfully with both entry modes.

#### Manual Verification:

- Save a purchase in manual mode without selecting a PDF and confirm the UI shows an estimated end date and status, with no document reference.
- Enter an explicit end date in manual mode and confirm it replaces the estimate and is identified as user-provided.
- Use PDF mode to preview, edit a suggested value, save, and confirm the corrected values and original PDF remain available.

**Implementation Note**: After completing this phase and its automated verification, pause for human confirmation that both entry modes work as expected before declaring the change complete.

## Testing Strategy

### Unit Tests:

- Test private and business estimate calculation, explicit-date precedence, date-basis output, February 29 clamping, active-through-end-date behavior, expiry after the end date, and unknown status when no effective date is available. Pass `today` explicitly to the calculation for deterministic cases.
- Test migration from the current required-document schema, including preservation of purchase metadata and existing document references.
- Test manual persistence without a PDF and retain tests for PDF validation, staged-file promotion, and rollback when PDF-backed saving fails.

### Integration Tests:

- Use the FastAPI test client to save a manual purchase without a file and verify the nullable document reference and computed result.
- Exercise the existing PDF preview, correction, and save path to verify the shared endpoint still persists corrected values and the original file.
- Reopen the SQLite profile after migration and verify existing purchase rows and document files remain usable.

### Manual Testing Steps:

1. Back up or copy a profile with a saved S-01 purchase, open it with the updated app, and verify the existing PDF-backed purchase remains available after migration.
2. Choose manual mode, enter required fields without selecting a PDF, save, and verify the estimate label, end date, status, and absence of a document reference.
3. Enter a custom end date and verify the result uses that date and identifies it as user-provided.
4. Choose PDF mode, preview and edit a suggested field, then save and confirm the corrected field and source PDF persist.

## Performance Considerations

Warranty date and status calculation is local and constant-time; it adds no OCR or external request to the save path. This change introduces no new latency target beyond the existing PRD requirements for the home screen and search.

## Migration Notes

- Back up the local profile before the first migration. Rebuild or otherwise migrate the SQLite purchase table to allow a nullable `document_ref`, preserving all existing rows and non-null references; do not rewrite or relocate existing PDF files.
- Keep the migration idempotent and run it before purchase reads or writes that rely on the updated schema. Verify the current schema before altering it so a second startup does not repeat destructive work.
- Keep the stored `warranty_end_date` as the user's explicit override. Compute the effective date, basis, and status from the purchase fields when producing the response; do not persist a calculated estimate over the explicit value.
- A missing document reference is a valid manual purchase state. No synthetic PDF should be created to satisfy the former constraint.

## References

- Active scope and decisions: `context/changes/add-purchase-manually/change.md`
- Codebase feasibility and evidence: `context/changes/add-purchase-manually/research.md`
- S-02 outcome and dependencies: `context/foundation/roadmap.md`
- Warranty formula and user story: `10xdevs/context/foundation/prd.md`
- Prior PDF save contract: `context/archive/2026-10-06-add-purchase-from-pdf/plan.md`
- UOKiK guarantee guidance: https://prawakonsumenta.uokik.gov.pl/reklamacja/gwarancja/

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Optional-Document Persistence and Warranty Rules

#### Automated

- [x] 1.1 `uv run pytest tests/test_pdf_purchase_flow.py tests/test_warranty_calculation.py` passes for manual-only persistence, migration preservation of existing records and document references, existing PDF atomic-save behavior, private/business estimates, user override, February 29, inclusive end-date status, and unknown status when no effective date exists.

#### Manual

- [x] 1.2 On a copy of a profile containing an S-01 purchase, run the migration and confirm the existing purchase data and PDF remain readable and the profile can also store a row without a document reference.

### Phase 2: Shared API and Two-Mode Entry Page

#### Automated

- [ ] 2.1 `uv run pytest` passes the backend suite, including manual no-PDF requests, nullable document responses, warranty results, migration preservation, and the existing PDF correction/save flow.
- [ ] 2.2 `npm --prefix frontend run build` completes successfully with both entry modes.

#### Manual

- [ ] 2.3 Save a purchase in manual mode without selecting a PDF and confirm the UI shows an estimated end date and status, with no document reference.
- [ ] 2.4 Enter an explicit end date in manual mode and confirm it replaces the estimate and is identified as user-provided.
- [ ] 2.5 Use PDF mode to preview, edit a suggested value, save, and confirm the corrected values and original PDF remain available.