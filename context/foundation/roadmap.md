---
project: PamiętajGwarancje
version: 1
status: draft
created: 2026-10-06
updated: 2026-10-06
prd_version: 1
main_goal: speed
top_blocker: decisions
milestone_id: first-warranty-check
milestone_seq: 1
milestone_status: open
---

# Roadmap: PamiętajGwarancje

> Derived from `10xdevs/context/foundation/prd.md` (v1) + auto-researched codebase baseline.
> Edit-in-place; archive when superseded.
> Slices below are listed in dependency order. The "At a glance" table is the index.

## Milestone

**M-01: Pierwsze sprawdzenie gwarancji** — Status: open

- **Intent:** Użytkownik zapisuje zakup z PDF, poprawia odczytane dane i szybko sprawdza gwarancję bez przeszukiwania segregatora. Kamień obejmuje także ręczne dodawanie, wyszukiwanie oraz obsługę zapisanych zakupów.
- **Source materials:** `10xdevs/context/foundation/prd.md` (v1)
- **Done when:** every F-NN and S-NN below is `done`.
- **Scope anchors:** FR-001–FR-007, US-01.

## Vision recap

Osoby prywatne posiadające narzędzia lub sprzęt nie mają łatwego podglądu, czy gwarancja nadal obowiązuje. Po awarii piły szablastej autor pomysłu musiał przeszukać segregator, by dopiero wtedy odkryć, że gwarancja wygasła; dokumenty są przechowywane, ale ich aktualny status nie jest od razu widoczny.

## North star

**S-01: Użytkownik może dodać zakup z PDF i poprawić odczytane dane przed zapisem.**

Gwiazda przewodnia oznacza tu najmniejszy przepływ od początku do końca, którego dostarczenie pokazuje, że produkt rozwiązuje główny problem. Ten przepływ sprawdza podstawową ścieżkę opisaną w US-01, zanim dojdą pozostałe sposoby obsługi zakupów.

## At a glance

| ID   | Change ID                         | Outcome (user can …)                                       | Prerequisites | PRD refs                                | Status   |
| ---- | --------------------------------- | ---------------------------------------------------------- | ------------- | --------------------------------------- | -------- |
| F-01 | private-purchase-storage-boundary | (foundation) ustalić minimalną granicę prywatnego zapisu    | —             | Access Control; Non-Functional Requirements: prywatność danych | in-progress |
| S-01 | add-purchase-from-pdf              | dodać zakup z PDF, poprawić dane OCR i zapisać              | F-01          | US-01, FR-002, FR-003; Non-Functional Requirements: zachowanie ręcznych poprawek | in-progress |
| S-02 | add-purchase-manually              | dodać zakup ręcznie i zobaczyć jego status gwarancji        | F-01          | FR-001; Business Logic                  | blocked  |
| S-03 | search-purchases-by-name           | znaleźć zapisany zakup po nazwie produktu                   | S-01, S-02   | US-01, FR-005; Non-Functional Requirements: wynik wyszukiwania w ciągu 3 sekund | proposed |
| S-04 | edit-saved-purchase                | edytować zapisany zakup                                     | S-02          | FR-006; Non-Functional Requirements: zachowanie ręcznych poprawek | proposed |
| S-05 | delete-purchase-or-document        | usunąć zapisany zakup albo dokument                        | S-01, S-02   | FR-007; Access Control                  | proposed |
| S-06 | view-expiring-warranties           | zobaczyć wkrótce wygasające gwarancje na ekranie głównym    | S-01, S-02   | US-01, FR-004; Non-Functional Requirements: ekran główny w ciągu 3 sekund | blocked  |

## Baseline

What's already in place in the codebase as of `2026-10-06` (auto-researched + user-confirmed).
Foundations below assume these are present and do NOT re-scaffold them.

- **Frontend:** absent — brak frameworka UI ani konfiguracji aplikacji; root `package.json` nie jest aplikacją Astro.
- **Backend / API:** partial — FastAPI i Uvicorn są zależnościami w `pyproject.toml`, ale `src/warranties_10xdev/__init__.py` zawiera tylko funkcję powitalną, bez aplikacji API.
- **Data:** absent — brak sterownika bazy danych, ORM, schematu i migracji.
- **Auth:** absent — brak dostawcy, sesji/tokenów i middleware; PRD zakłada na początek lokalny profil.
- **Deploy / infra:** partial — `context/foundation/infrastructure.md` rekomenduje Fly.io, ale brak konfiguracji wdrożenia i CI/CD. Założenia o procesie w tle i globalnym ruchu nie wynikają z PRD MVP, więc ta rekomendacja nie ustala zakresu.
- **Observability:** absent — brak wdrożonego logowania aplikacyjnego, śledzenia błędów i metryk.

## Foundations

### F-01: Minimalna granica prywatnego zapisu

- **Outcome:** (foundation) Ustalono najmniejszy kontrakt przechowywania zakupów i dokumentów PDF, który zachowuje prywatność lokalnego profilu i pozwala pierwszemu przepływowi zapisywać dane. Nie obejmuje całej warstwy danych ani przyszłych kont.
- **Change ID:** private-purchase-storage-boundary
- **PRD refs:** Access Control; Non-Functional Requirements: prywatność danych
- **Unlocks:** S-01 i S-02; weryfikacja, że dane zakupów i PDF są dostępne wyłącznie właścicielowi profilu.
- **Prerequisites:** —
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:** Jaki orientacyjny ruch i wolumen przechowywanych dokumentów należy zakładać? — Owner: user. Block: yes.
- **Risk:** Założenia o wolumenie wpływają na wybór minimalnego sposobu przechowywania; pełne projektowanie warstwy danych przed pierwszym zapisem byłoby przedwczesne.
- **Status:** in-progress

## Slices

### S-01: Dodanie zakupu z PDF

- **Outcome:** Użytkownik może dodać zakup z PDF, sprawdzić i poprawić dane odczytane przez OCR przed zapisem oraz zachować te poprawki.
- **Change ID:** add-purchase-from-pdf
- **PRD refs:** US-01, FR-002, FR-003; Non-Functional Requirements: zachowanie ręcznych poprawek
- **Prerequisites:** F-01
- **Parallel with:** S-02
- **Blockers:** —
- **Unknowns:**
  - Które pola są obowiązkowe przy zapisie zakupu? — Owner: user. Block: yes.
- **Risk:** Błędny odczyt OCR nie może nadpisać poprawek użytkownika ani dopuścić do zapisu bez wymaganych danych.
- **Status:** in-progress

### S-02: Ręczne dodanie zakupu

- **Outcome:** Użytkownik może ręcznie dodać zakup i zobaczyć wyliczony status oraz koniec gwarancji.
- **Change ID:** add-purchase-manually
- **PRD refs:** FR-001; Business Logic
- **Prerequisites:** F-01
- **Parallel with:** S-01
- **Blockers:** —
- **Unknowns:**
  - Które pola są obowiązkowe przy zapisie zakupu? — Owner: user. Block: yes.
- **Risk:** Domyślny termin zależy od rodzaju zakupu, a termin podany przez użytkownika ma go zastąpić.
- **Status:** blocked

### S-03: Wyszukiwanie po nazwie produktu

- **Outcome:** Użytkownik może znaleźć zapisany zakup, wyszukując po nazwie produktu.
- **Change ID:** search-purchases-by-name
- **PRD refs:** US-01, FR-005; Non-Functional Requirements: wynik wyszukiwania w ciągu 3 sekund
- **Prerequisites:** S-01, S-02
- **Parallel with:** S-04, S-05, S-06
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Wyniki muszą obejmować zakupy z obu ścieżek i nie mogą ujawniać danych innego profilu.
- **Status:** proposed

### S-04: Edycja zapisanego zakupu

- **Outcome:** Użytkownik może zmienić dane zapisanego zakupu.
- **Change ID:** edit-saved-purchase
- **PRD refs:** FR-006; Non-Functional Requirements: zachowanie ręcznych poprawek
- **Prerequisites:** S-02
- **Parallel with:** S-01, S-03, S-05, S-06
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Zmiana danych musi aktualizować status gwarancji bez utraty ręcznych poprawek.
- **Status:** proposed

### S-05: Usuwanie zakupu lub dokumentu

- **Outcome:** Użytkownik może usunąć zapisany zakup albo powiązany z nim dokument.
- **Change ID:** delete-purchase-or-document
- **PRD refs:** FR-007; Access Control
- **Prerequisites:** S-01, S-02
- **Parallel with:** S-03, S-04, S-06
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Usunięcie dokumentu nie powinno przypadkowo usuwać zakupu, jeśli użytkownik chce zachować jego dane.
- **Status:** proposed

### S-06: Gwarancje wkrótce wygasające

- **Outcome:** Użytkownik może zobaczyć na ekranie głównym zakupy, których gwarancje wkrótce wygasają.
- **Change ID:** view-expiring-warranties
- **PRD refs:** US-01, FR-004; Non-Functional Requirements: ekran główny w ciągu 3 sekund
- **Prerequisites:** S-01, S-02
- **Parallel with:** S-03, S-04, S-05
- **Blockers:** —
- **Unknowns:**
  - Jaki przedział czasu oznacza, że gwarancja wkrótce wygasa? — Owner: user. Block: yes.
- **Risk:** Bez uzgodnionego przedziału lista może pokazywać nieoczekiwane zakupy albo pomijać te, które użytkownik chce zauważyć.
- **Status:** blocked

## Backlog Handoff

| Roadmap ID | Change ID                         | Suggested issue title                        | Ready for `/10x-plan` | Notes                                      |
| ---------- | --------------------------------- | -------------------------------------------- | --------------------- | ------------------------------------------ |
| F-01       | private-purchase-storage-boundary | Ustalić minimalną granicę prywatnego zapisu   | no                    | Najpierw rozstrzygnąć pytanie o wolumen.   |
| S-01       | add-purchase-from-pdf              | Dodać zakup z PDF z korektą OCR               | no                    | Wymaga F-01 i decyzji o wymaganych polach. |
| S-02       | add-purchase-manually              | Dodać zakup ręcznie i pokazać status          | no                    | Wymaga F-01 i decyzji o wymaganych polach. |
| S-03       | search-purchases-by-name           | Wyszukiwać zakupy po nazwie produktu          | no                    | Czeka na S-01 i S-02.                     |
| S-04       | edit-saved-purchase                | Edytować zapisany zakup                       | no                    | Czeka na S-02.                            |
| S-05       | delete-purchase-or-document        | Usuwać zakup lub dokument                     | no                    | Czeka na S-01 i S-02.                     |
| S-06       | view-expiring-warranties           | Pokazać wkrótce wygasające gwarancje           | no                    | Czeka na S-01, S-02 i definicję terminu.   |

## Open Roadmap Questions

1. **Które pola są obowiązkowe przy zapisie zakupu?** — Owner: user. Block: S-01, S-02.
2. **Jaki przedział czasu oznacza, że gwarancja wkrótce wygasa?** — Owner: user. Block: S-06.
3. **Jaki orientacyjny ruch i wolumen przechowywanych dokumentów należy zakładać?** — Owner: user. Block: F-01.

## Parked

- **OCR ze zdjęć.** Why parked: PRD wyklucza zdjęcia z MVP; pierwsza wersja obsługuje PDF.
- **Współdzielenie zakupów i dokumentów.** Why parked: PRD wyklucza współdzielenie; dane pozostają prywatne dla właściciela.
- **Wyszukiwanie po kategorii.** Why parked: PRD ogranicza pierwszą wersję do wyszukiwania po nazwie produktu.
- **Przypomnienia przed końcem gwarancji.** Why parked: PRD wyklucza je z MVP.
- **Natywna aplikacja mobilna.** Why parked: PRD określa pierwszą wersję jako webową.

## Milestone History

(Empty on first milestone.)

## Done

(Empty on first generation. `/10x-archive` appends completed items.)