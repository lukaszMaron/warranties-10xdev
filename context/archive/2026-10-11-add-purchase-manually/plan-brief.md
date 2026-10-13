# Add Purchase Manually — Plan Brief

> Full plan: `context/changes/add-purchase-manually/plan.md`
> Research: `context/changes/add-purchase-manually/research.md`

## What & Why

Add a manual purchase workflow that saves without a PDF and immediately shows the warranty end date and status. The existing PDF-assisted flow stays available. Dates calculated from the PRD's private/business rule will be labeled estimates so users can distinguish them from dates supplied by a guarantee document.

## Starting Point

S-01 already provides purchase validation, private profile persistence, PDF preview/correction, and PDF-backed saving. Its current API, form, and database schema require a PDF, and the saved response has no computed warranty status.

## Desired End State

The existing purchase page offers explicit manual and PDF-assisted modes. A manual purchase saves with a nullable document reference; an uploaded PDF continues to use the existing private storage and rollback path. The response and UI distinguish the user's end-date override from the effective date and its `active`, `expired`, or `unknown` status.

## Key Decisions Made

| Decision | Choice | Why | Source |
| --- | --- | --- | --- |
| Required fields | Product name, purchase date, and purchase type; seller, payment method, and end-date override optional | Reuses S-01's validated contract and supplies inputs for the PRD formula | Plan / S-01 research |
| Default end date | PRD private/business calendar-year rule, explicitly labeled as an estimate; user-entered date overrides it | Preserves the PRD behavior without presenting it as the guarantor's actual term | Plan / PRD / UOKiK research |
| Date boundary | Active through the end date; expired the following day; February 29 maps to February 28 in a non-leap target year | Gives date comparisons a deterministic inclusive boundary | Plan |
| Missing effective date | Show `unknown` status | Avoids inferring coverage when no date can be established | Plan |
| Document model | Nullable document reference with a migration preserving S-01 rows and files | Supports manual entry without fabricating a PDF or splitting the purchase model | Plan / Research |
| Entry UX | Two explicit modes on the existing purchase page | Reuses the existing form surface while keeping manual entry independent of OCR | Plan |
| Calculated values | Derive effective date, basis, and status; retain the stored date as the user override | Prevents a computed estimate from overwriting its source value | Plan |

## Scope

**In scope:** PDF-free purchase persistence; preserving the existing PDF path; warranty estimate/override/status; nullable document migration; manual and PDF-assisted modes; synchronizing the PRD, roadmap details, and active change notes.

**Out of scope:** Tracking statutory seller responsibility or repair-related guarantee extensions; “expiring soon” logic or dashboard; search, edit, delete, reminders, OCR for the manual mode, and multiple documents per purchase.

## Architecture / Approach

Keep one purchase API and make its PDF upload optional. Reuse the current purchase input/validation and profile lock; migrate the existing SQLite table to allow a null document reference. Store only a user-provided warranty end date and derive the effective date, basis, and status for the response. The existing page will have separate manual and PDF-assisted modes.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Optional-document persistence and warranty rules | Safe migration, PDF-free persistence, and deterministic date/status calculation | Preserving existing document references while changing the SQLite constraint |
| 2. Shared API and two-mode entry page | Manual save and status display alongside the existing PDF workflow | Avoiding regressions in PDF preview, corrections, and file-backed save |

**Prerequisites:** F-01 is complete; product decisions were confirmed in planning. Back up or copy a profile before verifying the migration.
**Estimated effort:** Two implementation phases; effort is mainly the database migration and cross-layer verification.

## Open Risks & Assumptions

- The PRD formula is a product estimate, not a legal determination of the guarantor's actual terms; the UI must label it accordingly.
- S-06's “soon expiring” interval remains unresolved and is intentionally outside S-02.
- Existing local profiles may contain S-01 rows and PDFs, so migration verification must confirm they remain intact.

## Success Criteria (Summary)

- A manual purchase can be saved without a PDF and returns an effective date, its basis, and status.
- A user-entered end date overrides the estimate; the end date remains active through that calendar day.
- The existing PDF preview, user corrections, private file persistence, and save flow continue to work.