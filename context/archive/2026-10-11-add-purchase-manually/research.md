---
date: 2026-10-11T22:11:55+02:00
researcher: GitHub Copilot
git_commit: 7b01d3ea6b71581361c648d0374b4f90da1f409a
branch: develop
repository: warranties-10xdev
topic: "Can add-purchase-manually be implemented from the active change notes?"
tags: [research, codebase, purchases, warranty, storage]
status: complete
last_updated: 2026-10-11
last_updated_by: GitHub Copilot
---

# Research: Feasibility of add-purchase-manually

**Date**: 2026-10-11T22:11:55+02:00  
**Researcher**: GitHub Copilot  
**Git Commit**: 7b01d3ea6b71581361c648d0374b4f90da1f409a  
**Branch**: develop  
**Repository**: warranties-10xdev

## Research Question

Can S-02, `add-purchase-manually`, be implemented based on the active [change notes](change.md)?

## Summary

S-02 is technically feasible, but the active change notes and roadmap do not yet provide a decision-complete implementation contract. The existing purchase fields, validation, profile storage, and locking can be reused. In the inspected save route, a PDF upload is required, and the purchase table requires a document reference, so manual-only persistence needs a deliberate API/UI path and a compatible schema migration.

The PRD specifies an application rule: for a private purchase, use two years from purchase date; for a business purchase, use one year from purchase date; a user-entered alternate date overrides that result. It also requires a displayed end date and status ([PRD:83-87](../../../10xdevs/context/foundation/prd.md#L83-L87)). The active PRD and S-02 roadmap still leave required fields as a user-owned open question, while the archived S-01 plan documents one proposed field set. Confirm that set and clarify status/date-boundary behavior before planning implementation.

The PRD's date formula is a product rule, not a statement of Polish guarantee law. UOKiK describes commercial guarantee duration as set by the guarantor and, if unspecified for a consumer, presumed to be two years from delivery. Its guidance also distinguishes guarantee rights from statutory seller responsibility ([UOKiK: Gwarancja](https://prawakonsumenta.uokik.gov.pl/reklamacja/gwarancja/)). The PRD formula should not be represented as a legal determination without a product/legal decision.

## Detailed Findings

### Reusable purchase and private-storage paths

- `PurchaseInput` contains product name, purchase date, purchase type, seller, payment method, and optional warranty end date. `_validate_purchase` validates those values separately from PDF validation ([purchases.py:22-31,106-132](../../../src/warranties_10xdev/purchases.py#L22-L31), [purchases.py:106-132](../../../src/warranties_10xdev/purchases.py#L106-L132)).
- `ProfileStorage` provides the configured profile database and a profile lock; the S-01 persistence function uses that lock ([storage.py:21-51](../../../src/warranties_10xdev/storage.py#L21-L51), [purchases.py:49-67](../../../src/warranties_10xdev/purchases.py#L49-L67)). This is reusable for owner-private manual records.
- The archived S-01 plan explicitly puts manual-only purchase creation in S-02, and specifies `product_name`, `purchase_date`, and `purchase_type` as required while seller, payment method, and custom warranty end date are optional ([plan.md:31-35,83-87](../../../context/archive/2026-10-06-add-purchase-from-pdf/plan.md#L31-L35), [plan.md:83-87](../../../context/archive/2026-10-06-add-purchase-from-pdf/plan.md#L83-L87)). This is an existing implementation contract, but not evidence that the still-open user decision was accepted.

### PDF coupling that S-02 must address

- In the inspected `POST /api/purchases` handler, `file: UploadFile = File(...)` is mandatory and the handler reads PDF bytes before calling persistence ([api.py:51-77](../../../src/warranties_10xdev/api.py#L51-L77)).
- `save_purchase` accepts `pdf_bytes`, validates the PDF, stages it, and stores a generated document reference ([purchases.py:49-77](../../../src/warranties_10xdev/purchases.py#L49-L77)). The current table declares `document_ref TEXT NOT NULL UNIQUE` ([purchases.py:161-173](../../../src/warranties_10xdev/purchases.py#L161-L173)). The saved-purchase TypeScript contract also types `document_ref` as a non-null string ([api.ts:15-25](../../../frontend/src/lib/api.ts#L15-L25)).
- In the current add-purchase page, `canSave()` requires a selected file and submission passes that file to `savePurchase` ([new.astro:133-150,233-244](../../../frontend/src/pages/purchases/new.astro#L133-L150), [new.astro:233-244](../../../frontend/src/pages/purchases/new.astro#L233-L244)). The test named `test_api_accepts_manual_completion_without_preview` still uploads `receipt.pdf`; it proves manual field completion without OCR, not creation without a document ([test_pdf_purchase_flow.py:203-223](../../../tests/test_pdf_purchase_flow.py#L203-L223)).
- `_create_purchase_schema` uses `CREATE TABLE IF NOT EXISTS`. In the inspected `src/` tree, no migration file or `ALTER TABLE` path was found. If the chosen design permits a missing `document_ref`, changing the create-table declaration alone will not update an existing S-01 database; add and test a migration that preserves existing purchase/document references, or choose another explicit representation. Avoid a fabricated placeholder PDF, which would misrepresent a document as user-provided evidence.

### Warranty behavior and external guidance

- The PRD requires an end date and status. Its current formula uses purchase type and purchase date, with an explicitly entered alternate date replacing the default ([PRD:85-87](../../../10xdevs/context/foundation/prd.md#L85-L87)). The roadmap's S-02 outcome likewise promises a calculated status and end date ([roadmap:94-103](../../../context/foundation/roadmap.md#L94-L103)).
- The S-02 roadmap does not define status values or the exact date comparison for active versus expired. It assigns the undefined “soon expiring” window to S-06 ([roadmap:145-153](../../../context/foundation/roadmap.md#L145-L153)); that separate window need not be invented for S-02, but S-02 still needs an explicit minimal status contract.
- UOKiK's consumer guidance says commercial guarantee duration is determined by the guarantor; if the guarantor does not specify a period, it is presumed to be two years from delivery. UOKiK also notes that a qualifying replacement or significant repair can restart the period and other service cases can extend it. The source distinguishes guarantee rights from statutory seller responsibility ([UOKiK: Gwarancja](https://prawakonsumenta.uokik.gov.pl/reklamacja/gwarancja/)). The PRD's private/business formula is therefore an application assumption, not a complete model of actual guarantee terms or statutory rights. S-01 stores a user-entered end date but does not calculate this status ([change.md:24-26](change.md#L24-L26)).

## Feasibility and Handoff

- **Technical feasibility:** yes. Reuse `PurchaseInput`, its field validation, `ProfileStorage`, and the profile lock; keep the PDF save behavior intact for S-01.
- **Required technical work:** provide a manual-entry UI and a PDF-free save contract; decide whether that is a separate route or a shared optional-document route; represent absence of a document explicitly; migrate existing S-01 databases if the schema changes; make API response types reflect the chosen nullable/document contract; test manual-only insert and existing-row preservation.
- **Product decisions still needed:** confirm the required fields (the archived S-01 plan proposes three required fields, but the PRD and active S-02 roadmap still mark the question open); decide whether the PRD's private/business date formula is an intentional product estimate or is meant to represent actual guarantee coverage; define behavior when the warranty date is absent and the active/expired boundary. The S-06 “soon expiring” threshold remains separate.
- **Implementation readiness:** research supports a plan after those decisions are recorded. It does not authorize implementation or make the decisions on the user's behalf.

## Code References

- `src/warranties_10xdev/api.py:51-77` — current PDF-required purchase endpoint.
- `src/warranties_10xdev/purchases.py:22-31,49-77,106-132,161-205` — purchase contracts, validation, persistence, and current document constraint.
- `src/warranties_10xdev/storage.py:21-51,101-126` — private profile storage and initialization.
- `frontend/src/pages/purchases/new.astro:133-150,233-244` — selected-file requirement in the current UI.
- `frontend/src/lib/api.ts:15-25` — saved purchase response type.
- `tests/test_pdf_purchase_flow.py:203-223` — manual completion test that still includes a PDF.
- `10xdevs/context/foundation/prd.md:83-103` — warranty business rule and unresolved required-fields question.
- `context/foundation/roadmap.md:94-103,145-153,170-171` — S-02 outcome, blockers, and S-06 window question.

## Historical Context (from prior changes)

- **Supported:** The archived S-01 plan identifies manual-only purchase creation as S-02 and scopes S-01 to a PDF-backed flow ([plan.md:31-35](../../../context/archive/2026-10-06-add-purchase-from-pdf/plan.md#L31-L35)).
- **Supported as an implemented S-01 contract:** The archived plan lists three required fields and three optional fields ([plan.md:83-87](../../../context/archive/2026-10-06-add-purchase-from-pdf/plan.md#L83-L87)).
- **Unresolved against current product records:** The S-01 plan says the required-field decision was settled, but the current PRD and S-02 roadmap still list it as user-owned and blocking ([PRD:103](../../../10xdevs/context/foundation/prd.md#L103), [roadmap:102-103](../../../context/foundation/roadmap.md#L102-L103)). The inspected artifacts do not show a user confirmation that reconciles these statements.
- **No longer applicable baseline:** The archived S-01 plan's initial baseline says there was no API, purchase schema, or frontend. Current `api.py`, `purchases.py`, and `frontend/src/pages/purchases/new.astro` contain those components; do not use that historical baseline as current state ([plan.md:7-20](../../../context/archive/2026-10-06-add-purchase-from-pdf/plan.md#L7-L20)).

## Related Research

- The active change notes contain the prior UOKiK/consumer-protection findings in [change.md](change.md).

## Open Questions

1. Does the user confirm `product_name`, `purchase_date`, and `purchase_type` as the required set, with seller, payment method, and warranty end date optional?
2. Should the private/business date formula be presented as a product estimate, or should the app require/document the actual guarantor term and delivery basis?
3. What is the minimal status contract for S-02 (including missing end date and the exact active/expired boundary)? The S-06 “soon expiring” interval remains a separate open question.
4. Should a purchase without a PDF store a null document reference, or should the data model represent documents separately from purchases? The existing S-01 database schema requires a reference either way unless migrated.
