---
date: 2026-10-17T13:09:03+02:00
researcher: Łukasz Maroń
git_commit: 177eda8
branch: develop
repository: lukaszMaron/warranties-10xdev
topic: "Test-plan Phase 1 — PDF and warranty contracts (risks #1, #4)"
tags: [research, test-plan, pdf-extraction, purchases, warranty, api, frontend]
status: complete
last_updated: 2026-10-17
last_updated_by: Łukasz Maroń
last_updated_note: "Follow-up 2: ostrzeżenie dla terminu dłuższego niż szacunek wg rodzaju zakupu; serwer liczy w UTC, frontend wyświetla wg lokalizacji (zastępuje decyzję 4 z Follow-up 1)"
---

# Research: Test-plan Phase 1 — PDF and warranty contracts

**Date**: 2026-10-17T13:09:03+02:00
**Researcher**: Łukasz Maroń
**Git Commit**: 177eda8 (working tree has unrelated uncommitted `.github/` changes; no source/test files modified)
**Branch**: develop
**Repository**: lukaszMaron/warranties-10xdev

## Research Question

Ground §3 Phase 1 of [test-plan.md](../../foundation/test-plan.md) ("PDF and warranty contracts", risks #1 and #4): what is the source-backed oracle for PDF import, manual correction and warranty date/status rules; how does the current code implement them; which seams can pytest unit + API integration tests use; and what does the existing suite already prove versus leave open?

## Summary

- **Oracle exists and is mostly precise.** PRD FR-002/003 plus the guardrail "Ręczne poprawki … nie są tracone" define the PDF contract ([prd.md:39](../../../10xdevs/context/foundation/prd.md), [:59](../../../10xdevs/context/foundation/prd.md), [:61](../../../10xdevs/context/foundation/prd.md)); PRD Business Logic defines warranty rules: private = 2 calendar years, business = 1 calendar year, user-supplied date replaces the estimate, end day inclusive, expired the next day, Feb 29 → Feb 28 in a non-leap target year, unknown when no end date can be established ([prd.md:85](../../../10xdevs/context/foundation/prd.md), [:87](../../../10xdevs/context/foundation/prd.md)). Required fields (product name, purchase date, purchase type) were decided in archived S-01/S-02 planning and are marked confirmed in [roadmap.md:172-173](../../foundation/roadmap.md); only the older `shape-notes.md:41, :134` still lists them as open (stale, see Open Questions).
- **Warranty rules (#4) are already well protected at unit level.** All 5 tests in [test_warranty_calculation.py](../../../tests/test_warranty_calculation.py) use hard-coded expected dates and an injected `today`; they cover the type-based estimate, user override, Feb 29 clamp and the inclusive boundary. Remaining gaps are narrow: business estimate at API level, deterministic `today` at API level, manual date + type change, and Feb 29 into a leap target year.
- **PDF field extraction (#1) is the weak spot.** Extraction is label-based regex over page text ([pdf_extraction.py:147](../../../src/warranties_10xdev/pdf_extraction.py)). Runtime probes on the current tree reproduced 4 mis-mapping/miss behaviours that none of the 30 tests in the 4 inspected PDF/warranty test files exercise (details below): first generic `Date:` wins over `Purchase date:`, `Product-ID: 123` becomes product name `ID: 123`, unknown labelled lines are absorbed into the previous field, and `DD-MM-YY` dates return `None`. The 7 tests in `test_pdf_extraction.py` use well-formed labelled input (per worker read of that file).
- **Correction preservation is a server-side non-issue but a client-side risk.** On the inspected save path ([api.py:51](../../../src/warranties_10xdev/api.py)) the server does not call extraction; it persists submitted form values. The "don't overwrite edits" logic is in the inline script of [new.astro:266](../../../frontend/src/pages/purchases/new.astro) (no equivalent found in `src/warranties_10xdev/`), which pytest cannot reach and which has no frontend test runner (test-plan §4).
- **Cheapest layers for Phase 1:** pure-function unit tests on `_suggest_fields` / `_normalize_date` (text in, no PDF/OCR) and `calculate_warranty(..., today=...)`; API integration via `TestClient` + `WARRANTIES_DATA_DIR` tmp profile for save/correction round-trips.

## Detailed Findings

### 1. Oracle — PDF import and correction (risk #1)

| Contract | Source |
|---|---|
| OCR reads purchase date, place/seller and payment method from a PDF receipt/invoice | [prd.md:59](../../../10xdevs/context/foundation/prd.md) (FR-002) |
| User can correct data read from PDF before saving | [prd.md:61](../../../10xdevs/context/foundation/prd.md) (FR-003) |
| OCR may misread fields; correction is the mitigation | [prd.md:60](../../../10xdevs/context/foundation/prd.md) |
| Manual corrections are not lost (guardrail) | [prd.md:39](../../../10xdevs/context/foundation/prd.md) |
| Suggested fields: `product_name`, `purchase_date`, `seller`, `payment_method`; `purchase_type` and `warranty_end_date` are user-entered, not OCR-inferred; per-field warnings | [archive add-purchase-from-pdf plan.md:37-40](../../archive/2026-10-06-add-purchase-from-pdf/plan.md) |
| Required: product name, purchase date, purchase type; optional: seller, payment method, warranty end date | [archive plan-brief.md:20-31](../../archive/2026-10-06-add-purchase-from-pdf/plan-brief.md); [add-purchase-manually change.md:30-34](../add-purchase-manually/change.md) |
| Preview is non-persistent; only explicit Save persists corrected metadata + original PDF | [archive plan-brief.md:34-35](../../archive/2026-10-06-add-purchase-from-pdf/plan-brief.md) |
| Saved values are the corrected form values, not OCR suggestions | [archive plan.md:104-107](../../archive/2026-10-06-add-purchase-from-pdf/plan.md) |
| Extraction failure keeps the selected PDF, allows manual completion, never silently overwrites displayed values | [archive plan.md:84-87](../../archive/2026-10-06-add-purchase-from-pdf/plan.md) |
| OCR must not overwrite corrections nor allow saving without required data | [roadmap.md:84-89](../../foundation/roadmap.md) |

Not specified by any inspected source: amount/currency fields (none exist in contract or code), accepted textual date formats, D/M vs M/D ordering, behaviour on duplicate/conflicting labels.

### 2. Oracle — warranty date and status (risk #4)

| Rule | Source |
|---|---|
| Estimate = 2 calendar years from purchase date (private) / 1 calendar year (business); estimate only | [prd.md:85](../../../10xdevs/context/foundation/prd.md) |
| A different or extended user-entered date from the document replaces the estimate | [prd.md:85](../../../10xdevs/context/foundation/prd.md) |
| End date is active inclusive of that day; expired from the next day | [prd.md:87](../../../10xdevs/context/foundation/prd.md) |
| Unknown status when no end date can be established | [prd.md:87](../../../10xdevs/context/foundation/prd.md) |
| Feb 29 purchase with non-leap target year → Feb 28 | [prd.md:87](../../../10xdevs/context/foundation/prd.md) |
| Status values exactly `active`/`expired`/`unknown`; basis `user`/`estimate`/`unknown`; compare against local calendar date; tests pass `today` explicitly | [archive add-purchase-manually plan.md:101-119, 155-160](../../archive/2026-10-11-add-purchase-manually/plan.md) |
| Stored explicit `warranty_end_date` remains source; computed values must not overwrite it | [archive add-purchase-manually plan.md:44-48, 188-192](../../archive/2026-10-11-add-purchase-manually/plan.md) |

Because durations are whole calendar years, Feb 29 is the only purchase date whose anniversary can be missing; general month-end rollover (e.g. Jan 31 + N months) is not a reachable case under this rule. Not specified: timezone for "today", whether a manual end date earlier than the purchase date is valid, and the "expiring soon" threshold (out of Phase 1 scope — S-07, [prd.md:101-104](../../../10xdevs/context/foundation/prd.md)).

### 3. Current implementation — PDF extraction

- `extract_pdf_suggestions(pdf_bytes)` ([pdf_extraction.py:31](../../../src/warranties_10xdev/pdf_extraction.py)) uses `pypdfium2`; per-page embedded text, Tesseract `pol+eng` OCR fallback for pages without text ([:54](../../../src/warranties_10xdev/pdf_extraction.py), [:74](../../../src/warranties_10xdev/pdf_extraction.py)). OCR failure produces warnings, not an exception.
- `_suggest_fields(text, ocr_warnings)` ([:100](../../../src/warranties_10xdev/pdf_extraction.py)) returns exactly 4 fields plus a `warnings` dict keyed by each field whose value is `None`. **Pure function — testable with a string, no PDF/OCR.**
- `_FIELD_LABELS` ([:133](../../../src/warranties_10xdev/pdf_extraction.py)) includes generic labels `product`, `item`, `date`, `data`, `store`, `payment`.
- `_label_value` ([:147](../../../src/warranties_10xdev/pdf_extraction.py)): regex `label\s*[:\-]\s*(.+?)` lazily captured until the next *known* label followed by `:`/`-`, or end of text; `re.DOTALL`; first match by text position wins.
- `_normalize_date` ([:163](../../../src/warranties_10xdev/pdf_extraction.py)): tries `%Y-%m-%d`, `%d.%m.%Y`, `%d/%m/%Y`, `%d-%m-%Y`, `%d.%m.%y`, `%d/%m/%y` (6 formats; no `%d-%m-%y`). Returns ISO date or `None`.

**Runtime probes (this session, `uv run python`, current tree)** — observed outputs:

| Input | Observed | Oracle-relevant problem |
|---|---|---|
| `_normalize_date("05-03-26")` | `None` | Dashed 2-digit year matched by the candidate regex but no format → silently missing |
| `_normalize_date("05.03.26")`, `("05/03/26")`, `("2026-3-5")` | `2026-03-05` | — |
| `_normalize_date("03/05/2026")` | `2026-05-03` | D/M ordering assumed; not specified by oracle |
| `_normalize_date("31.02.2026")`, `("05.03/2026")` | `None` | Correct rejection (invalid date / mixed separators) |
| `"Date: 2026-01-10 Purchase date: 2026-01-05 …"` | `purchase_date='2026-01-10'` | Generic earlier `Date:` beats explicit `Purchase date:` → mis-mapped |
| `"Product-ID: 123 Product name: Laptop …"` | `product_name='ID: 123'` | `-` separator lets `Product-ID` match `product` label → mis-mapped |
| `"Sprzedawca: Sklep X\nNIP: 123\nData: …"` | `seller='Sklep X\nNIP: 123'` | Unknown labelled line absorbed into previous field |
| `"Product: TV\nWarranty: 24 months\nSeller: ACME"` | `product_name='TV\nWarranty: 24 months'` | Same absorption |
| `"Produkt: Kabel USB\nSposób płatności: karta"` | product `Kabel USB`, payment `karta` | Polish labels work (earlier `None` was a PowerShell pipe encoding artefact, re-checked with `\u` escapes) |

Whether these behaviours are bugs is an **oracle judgement**: FR-002/003 accept that OCR may misread, and correction is the mitigation. A test must decide which of them the product promises to get right (see Open Questions).

### 4. Current implementation — API preview and save

- Module-global `app = FastAPI(...)` ([api.py:23](../../../src/warranties_10xdev/api.py)); no app factory. Collaborators are module-level imports, monkeypatchable as `api.extract_pdf_suggestions`, `api.persist_purchase`, `api.ProfileStorage`.
- `POST /api/purchases/preview` ([api.py:39-49](../../../src/warranties_10xdev/api.py)): bounded read (413 above 20 MiB), 422 for non-`%PDF-` prefix or `PdfExtractionError`, returns `asdict(PdfSuggestions)`. No persistence.
- `POST /api/purchases` ([api.py:51](../../../src/warranties_10xdev/api.py)): multipart form; `product_name`, `purchase_date: date`, `purchase_type: Literal["private","business"]` required; `seller`, `payment_method`, `warranty_end_date` optional; optional `file`. On this inspected path the server does **not** call extraction — submitted values are what gets stored. `calculate_warranty(purchase)` is called with no `today` ([api.py:71](../../../src/warranties_10xdev/api.py)), so API responses depend on `date.today()`.
- Validation `_validate_purchase` ([purchases.py:118](../../../src/warranties_10xdev/purchases.py)): product name stripped and non-blank; seller/payment stripped, blank → `None`; manual end date must be a `date` (no ordering check versus purchase date). Errors → 422; storage unavailable → 503; persistence failure → 500.
- Profile root injectable via `WARRANTIES_DATA_DIR` (pattern already used in [test_pdf_purchase_flow.py](../../../tests/test_pdf_purchase_flow.py)).

### 5. Current implementation — warranty calculation

`calculate_warranty(purchase, today=None)` ([purchases.py:254](../../../src/warranties_10xdev/purchases.py)):
- `None` purchase → `(None, "unknown", "unknown")`.
- Manual `warranty_end_date` present → used as-is, basis `user`, regardless of `purchase_type`.
- Otherwise `years = 2 if private else 1` ([:265](../../../src/warranties_10xdev/purchases.py)); same month/day in target year; `ValueError` → `date(target_year, 2, 28)` ([:272](../../../src/warranties_10xdev/purchases.py)).
- `today` defaults to `date.today()` ([:275](../../../src/warranties_10xdev/purchases.py)); `active` iff `today <= end` ([:277](../../../src/warranties_10xdev/purchases.py)).
- Computed values are returned in the save response; they are not persisted, and `api.py` defines 2 endpoints (preview, save) — no read/list endpoint to recompute later.

Code matches each PRD rule in §2 on the inspected path. With required-field validation, a valid purchase cannot currently produce `unknown`; `unknown` is reachable only via `None`.

### 6. Current implementation — frontend correction logic

In [new.astro](../../../frontend/src/pages/purchases/new.astro) inline script:
- `editedFields` set ([:169](../../../frontend/src/pages/purchases/new.astro)) filled on `input`/`change` of every `[data-draft-field]` ([:233-235](../../../frontend/src/pages/purchases/new.astro)).
- Preview fills a field only if `!hasReceivedSuggestions`, field not edited and suggestion truthy ([:266-275](../../../frontend/src/pages/purchases/new.astro)). Repeat preview of the same file is a no-op for values.
- Selecting a different file resets `hasReceivedSuggestions` but **not** `editedFields` or field values ([:205](../../../frontend/src/pages/purchases/new.astro)). Inference: un-edited values suggested from file A remain when file B lacks that field, and can be saved with file B.
- Save submits the live form via `FormData`; on error the form is untouched; on success `form.reset()` and `editedFields.clear()` ([:327-332](../../../frontend/src/pages/purchases/new.astro)).
- No frontend test runner exists (test-plan §4), so this logic is outside Phase 1's pytest layers. It belongs to Phase 3 (Playwright) unless the plan extracts the merge rule into a testable module.

### 7. Existing test coverage (`uv run pytest -q`: 63 passed, run by research worker this session)

| File | Tests | Relevant assertions |
|---|---|---|
| [test_warranty_calculation.py](../../../tests/test_warranty_calculation.py) | 5 | Type-based estimate (:29), user override keeps input (:42), Feb 29 → Feb 28 (:51), inclusive boundary (:64), `None` → unknown (:77). Hard-coded expected values; explicit `today`. |
| [test_pdf_extraction.py](../../../tests/test_pdf_extraction.py) | 7 | Embedded-text extraction (:33), mocked Polish OCR (:49), missing-field warnings (:71), malformed/encrypted/oversized rejection (:85, :90, :117), missing Tesseract (:101). Hand-built PDF via `_pdf()` (:9). Only well-formed labelled input. |
| [test_pdf_preview_api.py](../../../tests/test_pdf_preview_api.py) | 5 | Preview returns mocked suggestions without persisting (:10), 422/413 paths, exact size limit. |
| [test_pdf_purchase_flow.py](../../../tests/test_pdf_purchase_flow.py) | 13 | Corrected values + PDF persist across reopen (:69), API saves corrected values (:261), manual save without preview (:304, hard-coded `2027-04-03`), manual override basis `user` (:358), missing required / corrupt PDF rejection (:383), rollback paths. |

No `conftest.py`; no pytest config in `pyproject.toml`. No mirror tests found among the files above (expected values are literals). Weak assertion: [test_pdf_purchase_flow.py:261](../../../tests/test_pdf_purchase_flow.py) checks `status` only by membership because `today` is not controlled.

### 8. Gaps relative to Phase 1 goals

| Gap | Risk | Cheapest layer |
|---|---|---|
| Mis-mapping on realistic receipts: generic vs specific date label, `Product-ID`-style prefixes, absorbed unknown lines | #1 | Unit on `_suggest_fields` (text fixtures) |
| Date formats: `DD-MM-YY` returns `None`; D/M vs M/D undecided | #1 | Unit on `_normalize_date` (parametrised) |
| Corrected value for every editable field (incl. date corrected from bad OCR, whitespace stripping, blank optional → `None`) persisted exactly and re-read | #1 | API integration + reopen tmp profile |
| Preview → save round trip where saved values differ from preview suggestions for all 4 fields | #1 | API integration (preview with mocked extractor, then save) |
| Business estimate via API; deterministic status via API | #4 | API integration with patched `today`/`date` |
| Manual end date + `purchase_type` change keeps manual date | #4 | Unit |
| Feb 29 business purchase (2024-02-29 → 2025-02-28 per PRD) and Feb 28 purchase into a leap target year (2026-02-28 private → 2028-02-28, not Feb 29). A Feb 29 purchase cannot reach a leap target year with 1- or 2-year terms. | #4 | Unit, values from PRD rule |
| Frontend: new file after edits; un-edited stale suggestions | #1 | Not reachable by pytest — Phase 3 or extract-to-module decision |

## Code References

- `src/warranties_10xdev/pdf_extraction.py:31` — `extract_pdf_suggestions` entry point
- `src/warranties_10xdev/pdf_extraction.py:100` — `_suggest_fields` pure field mapper
- `src/warranties_10xdev/pdf_extraction.py:133` — `_FIELD_LABELS`
- `src/warranties_10xdev/pdf_extraction.py:147` — `_label_value` regex
- `src/warranties_10xdev/pdf_extraction.py:163` — `_normalize_date`
- `src/warranties_10xdev/api.py:39` — preview endpoint
- `src/warranties_10xdev/api.py:51` — save endpoint; `:71` warranty without `today`
- `src/warranties_10xdev/purchases.py:118` — `_validate_purchase`
- `src/warranties_10xdev/purchases.py:254` — `calculate_warranty`
- `frontend/src/pages/purchases/new.astro:205` — file change resets suggestions flag only
- `frontend/src/pages/purchases/new.astro:266` — preview merge rule

## Architecture Insights

- Extraction suggestions and persistence are decoupled: the server trusts the submitted form, so "correction preserved" on the backend reduces to "submitted value persisted exactly". The real overwrite risk is in the client merge rule.
- `calculate_warranty` has an explicit `today` seam; the API does not pass one, so API-level status tests need monkeypatching (e.g. `purchases.date`) or a new seam — a planning decision.
- Test style already in repo: literal expected values, `tmp_path` profiles, `TestClient(api.app)`, hand-built PDF bytes, monkeypatched collaborators. Phase 1 can follow it without new tooling.

## Historical Context (from prior changes)

- [archive/2026-10-06-add-purchase-from-pdf/plan.md](../../archive/2026-10-06-add-purchase-from-pdf/plan.md) — field mapping, preview non-persistence, "never silently overwrite" UI rule. Supported by current code on inspected paths, except new-file selection which does not clear edits/values (inference).
- [archive/2026-10-11-add-purchase-manually/plan.md](../../archive/2026-10-11-add-purchase-manually/plan.md) — status/basis values, explicit `today` in tests. Supported.
- [changes/add-purchase-manually/change.md](../add-purchase-manually/change.md) — required fields and warranty rules "confirmed during planning". Supported by code; [shape-notes.md:134](../../../10xdevs/context/foundation/shape-notes.md) still shows the pre-decision open question (stale).
- [archive/2026-10-13-purchase-entry-ui-contract/research.md](../../archive/2026-10-13-purchase-entry-ui-contract/research.md) — preview/save status messages and pending states; UI-only, not Phase 1 scope.

## Related Research

- [archive/2026-10-11-add-purchase-manually/research.md](../../archive/2026-10-11-add-purchase-manually/research.md)
- [archive/2026-10-13-purchase-entry-ui-contract/research.md](../../archive/2026-10-13-purchase-entry-ui-contract/research.md)

## Open Questions

> Status 2026-10-17: pytania 1, 2, 4, 5 i 6 rozstrzygnął właściciel — patrz [Follow-up 2026-10-17](#follow-up-2026-10-17--decyzje-właściciela). Pytanie 3 pozostaje niskiego ryzyka (decyzja z roadmapy obowiązuje).

Owner decisions needed before writing assertions (oracle must not be copied from code):

1. **Extraction precision promise.** Should tests assert that a specific `Purchase date:` beats a generic `Date:`, that `Product-ID:` is not a product name, and that unknown labelled lines are not absorbed — or only that wrong suggestions remain correctable? This decides whether the probe findings are bugs (red tests) or accepted OCR imperfection.
2. **Date formats.** Which textual formats must be recognised (e.g. `DD-MM-YY`)? Is D/M ordering the intended rule for Polish documents?
3. **Required-field source of truth (low risk).** [shape-notes.md:41, :134](../../../10xdevs/context/foundation/shape-notes.md) still lists required fields as an owner question, while [roadmap.md:172-173](../../foundation/roadmap.md), archived plans and code use product name + purchase date + purchase type. Treat the roadmap/archived decision as the oracle unless the owner says otherwise.
4. **Manual end date before purchase date.** Accept, reject, or warn? Not specified; code accepts.
5. **"Today" timezone.** Archived plan says local calendar date; no timezone named. Matters only for API-level status tests.
6. **Frontend merge rule coverage.** Defer to Phase 3 Playwright, or extract the rule into a testable module now (requires a frontend test runner, which test-plan §4 lists as absent)?

## Follow-up 2026-10-17 — decyzje właściciela

Źródło: odpowiedź właściciela (Łukasz Maroń) w sesji badania, 2026-10-17. Decyzje stają się oracle dla fazy 1 obok PRD; nie wynikają z kodu.

| # | Decyzja | Konsekwencja dla testów fazy 1 | Stan kodu na `177eda8` |
|---|---|---|---|
| 1 | Błędne dopasowania z §3 (ogólne `Date:` przed `Purchase date:`, `Product-ID:` jako nazwa, wchłanianie nieznanej linii z etykietą, `DD-MM-YY`) **mają zostać naprawione**; ręczna korekta pozostaje. | 4 przypadki z tabeli prób w §3 stają się testami „red” na `_suggest_fields` / `_normalize_date`. Testy zachowania korekty (API) pozostają w zakresie. | Niezgodny: wszystkie 4 zachowania odtworzone w tej sesji. |
| 2 | Formaty dat zależą od **bieżących ustawień systemu** (regionalnych); daty ze znakiem `/` interpretujemy **zawsze** jako dzień/miesiąc/rok. | Reguła `/` = D/M/Y ma pierwszeństwo przed ustawieniami regionalnymi (także np. przy ustawieniach en-US). Pozostałe formaty: kolejność wg ustawień systemu. Testy muszą ustawiać locale jawnie (np. parametr/fixture), a nie polegać na maszynie CI. | Częściowo zgodny: `/` już jest D/M/Y ([pdf_extraction.py:163](../../../src/warranties_10xdev/pdf_extraction.py)); formaty są zakodowane na sztywno, kod nie odczytuje ustawień systemu (brak `locale` w `src/warranties_10xdev/`). |
| 3 (OQ4) | Ręczny termin **wcześniejszy niż data zakupu: dopuszczać z ostrzeżeniem**. Należy też umożliwić ustawienie terminu **dłuższego niż 2 lata**. | Ustalone: (a) termin wcześniejszy niż zakup — zapis się udaje, odpowiedź zawiera ostrzeżenie (kształt do ustalenia w planie); (b) termin > 2 lata — zapis się udaje, basis `user` (zgodne z [prd.md:85](../../../10xdevs/context/foundation/prd.md) — „przedłużony termin zastępuje szacunek”). **Nieustalone:** czy termin > 2 lata także ma generować ostrzeżenie. Odpowiedź właściciela dopuszcza oba odczytania; asercji o obecności/braku ostrzeżenia dla (b) nie pisać przed rozstrzygnięciem. | Częściowo zgodny: oba przypadki są akceptowane ([purchases.py:118](../../../src/warranties_10xdev/purchases.py)), ale ostrzeżenia brak w modelu odpowiedzi ([api.py:51](../../../src/warranties_10xdev/api.py)). |
| 4 (OQ5) — **zastąpione przez 4' w Follow-up 2** | „Dzisiaj” wyznacza **strefa czasowa urządzenia** użytkownika. | Testy statusu przekazują „dzisiaj”/strefę jawnie; jeden test graniczny z różnicą daty między UTC a strefą urządzenia (np. 23:30 w Europe/Warsaw vs UTC). | Ryzyko niezgodności: `calculate_warranty` używa `date.today()` procesu serwera ([purchases.py:275](../../../src/warranties_10xdev/purchases.py)). Na lokalnym profilu ([prd.md:91](../../../10xdevs/context/foundation/prd.md)) to strefa urządzenia; po wdrożeniu na Fly.io ([infrastructure.md:17](../../foundation/infrastructure.md)) byłaby to strefa serwera. |
| 5 (OQ6) | Logika scalania podpowiedzi w formularzu — **czekamy do fazy 3** (Playwright). | Faza 1 nie testuje [new.astro:205, :266](../../../frontend/src/pages/purchases/new.astro); scenariusz „inny PDF po edycji” przekazać do fazy 3. | Bez zmian. |

### Wnioski dla `/10x-plan`

- **Zakres zmienia się z „tylko testy” na „testy + poprawki”:** decyzje 1, 2 i 3 wymagają zmian w kodzie produkcyjnym (ekstrakcja, odczyt ustawień regionalnych, ostrzeżenie w odpowiedzi zapisu). Dobre kandydatki na `/10x-tdd` — każdą da się nazwać jednym zdaniem pierwszego czerwonego testu.
- **Ustawienia systemu i strefa urządzenia przy backendzie na serwerze:** jeśli API ma działać na Fly.io, ani `locale` serwera, ani `date.today()` serwera nie reprezentują urządzenia. Plan musi wybrać nośnik tych informacji (np. klient przesyła strefę/locale lub datę „dzisiaj”, albo status liczony w przeglądarce). Inferencja — nie rozstrzygnięta przez właściciela; dla lokalnego profilu obecne podejście jest zgodne.
- **Ostrzeżenie bez nowego kontraktu:** obecna odpowiedź zapisu nie ma pola ostrzeżeń; plan musi zdefiniować jego nazwę i kształt (np. analogicznie do `warnings` z podglądu, [pdf_extraction.py:100](../../../src/warranties_10xdev/pdf_extraction.py)).
- ~~**Otwarte pytanie do właściciela (blokuje tylko asercję dla terminu > 2 lata)**~~ — rozstrzygnięte w Follow-up 2 poniżej.

## Follow-up 2 (2026-10-17) — doprecyzowanie decyzji 3 i 4

Źródło: odpowiedź właściciela w sesji badania, 2026-10-17 13:24. Zastępuje wskazane wnioski z Follow-up 1.

| # | Decyzja | Konsekwencja dla testów fazy 1 | Stan kodu na `177eda8` |
|---|---|---|---|
| 3b | Ręczny termin dłuższy niż **szacunek według rodzaju zakupu** jest zapisywany **z ostrzeżeniem**. Punkt odniesienia: 2 lata dla prywatnego, 1 rok dla firmowego (ta sama reguła co [prd.md:85](../../../10xdevs/context/foundation/prd.md)). | Przykłady z reguły PRD: zakup prywatny 2026-03-10 → próg 2028-03-10; firmowy 2026-03-10 → próg 2027-03-10. Termin równy progowi — bez ostrzeżenia; dzień później — zapis + ostrzeżenie, basis `user`. Ten sam termin 2027-06-01 daje ostrzeżenie dla firmowego, a dla prywatnego nie. Zakup z 29 lutego: próg wg reguły Feb 28. | Niezgodny: zapis się udaje, ale odpowiedź nie ma pola ostrzeżeń ([api.py:51](../../../src/warranties_10xdev/api.py)). |
| 4' | **Serwer** wyznacza „dzisiaj” w **UTC**; **frontend** wyświetla daty według lokalizacji urządzenia. **Zastępuje** decyzję 4 z Follow-up 1 („strefa czasowa urządzenia”) w zakresie obliczania statusu. | Testy statusu ustalają „dzisiaj” jako datę UTC (wstrzyknięcie lub kontrolowany zegar UTC); test graniczny: chwila, gdy data lokalna i data UTC się różnią (np. 2026-10-18 00:30 w Europe/Warsaw, CEST = 2026-10-17 22:30 UTC) — status liczony z daty UTC 2026-10-17. Formatowanie wyświetlania jest zakresem frontendu — faza 3. | Niezgodny: `date.today()` używa lokalnej strefy procesu, nie UTC ([purchases.py:275](../../../src/warranties_10xdev/purchases.py)). Frontend ma na sztywno `pl-PL` i `timeZone: "UTC"` ([new.astro:302-304](../../../frontend/src/pages/purchases/new.astro)) — `timeZone: "UTC"` jest właściwy dla daty kalendarzowej, ale `pl-PL` nie odpowiada „lokalizacji urządzenia”. |

### Wnioski dla `/10x-plan` (aktualizacja)

- Nośnik strefy/locale z urządzenia do serwera (wniosek z Follow-up 1) **nie jest już potrzebny** dla statusu — serwer liczy w UTC.
- **Skutek akceptowany przez decyzję, wart odnotowania w planie:** w godzinach, gdy data lokalna użytkownika różni się od daty UTC (np. w Polsce 00:00–01:59 latem), status w dniu granicznym może różnić się od daty widzianej przez użytkownika o jeden dzień. Inferencja z decyzji 4' i [prd.md:87](../../../10xdevs/context/foundation/prd.md) („wygasły następnego dnia”); nie wymaga nowej decyzji, ale test graniczny powinien to udokumentować.
- **Decyzja 2 (formaty dat w ekstrakcji wg ustawień systemu) a serwer UTC:** decyzja 4' dotyczy daty „dzisiaj” i wyświetlania, nie parsowania tekstu z PDF. Dla ekstrakcji obowiązuje nadal: `/` = D/M/Y; kolejność pozostałych formatów wg ustawień systemu — przy backendzie na serwerze będą to ustawienia serwera. Plan powinien to jawnie przyjąć albo przekazywać locale z przeglądarki przy podglądzie.
- Zmiana `pl-PL` → locale przeglądarki (`undefined` w `Intl.DateTimeFormat`) to zmiana frontendu; weryfikacja w fazie 3 zgodnie z decyzją 5.
