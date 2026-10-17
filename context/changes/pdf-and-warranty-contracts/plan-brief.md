# PDF and warranty contracts — Plan Brief

> Full plan: `context/changes/pdf-and-warranty-contracts/plan.md`
> Research: `context/changes/pdf-and-warranty-contracts/research.md`

## What & Why

To faza 1 rolloutu z test-plan.md (ryzyka #1 i #4). Import PDF ma 4 odtworzone błędy podpowiedzi, a reguły dat i terminu gwarancji nie były zdefiniowane. Naprawiamy ekstrakcję, dodajemy ostrzeżenia dla ręcznego terminu i liczymy „dziś” w UTC. Każdą regułę zabezpieczamy testem, którego wyrocznią są decyzje właściciela, a nie obecny kod.

## Starting Point

- Ekstrakcja to czyste funkcje w `pdf_extraction.py`. Ogólne `Date:` wygrywa z `Purchase date:`, `Product-ID` staje się nazwą, wartość wchłania następną linię, a `DD-MM-YY` nie działa.
- API liczy status z lokalnego `date.today()`, a odpowiedź zapisu nie ma ostrzeżeń.
- Frontend formatuje daty na sztywno w `pl-PL`.
- Testy: 63 przechodzą.

## Desired End State

- Podpowiedzi z PDF są przewidywalne. Przy konflikcie lub niepewności pole zostaje puste i pojawia się ostrzeżenie; ręczna korekta zawsze działa.
- Zapis z nietypowym terminem gwarancji się udaje i zwraca ostrzeżenie, które widać w UI.
- Status liczy się od daty UTC, a daty w UI są w formacie ustawień przeglądarki.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Błędy dopasowań | Naprawić; ręczna korekta zostaje | Podpowiedź ma pomagać, a nie wprowadzać w błąd | Research |
| Kolejność dat | ISO = R-M-D; `/` = D/M/R; `.` i `-` według ustawień serwera | Zgodne z oczekiwaniem właściciela i ustawieniami systemu | Research |
| Ręczny termin | Zapis zawsze; ostrzeżenie, gdy termin < zakup lub > szacunek (prywatny +2 lata, firmowy +1 rok) | Nie blokuje wyjątkowych gwarancji, a sygnalizuje literówki | Research |
| „Dziś” | Data UTC na serwerze, zegar podmienialny w testach | Deterministyczny status; zaakceptowana różnica jednego dnia przy północy | Research |
| Testy scalania w UI | Odłożone do fazy 3 (Playwright) | To zachowanie przeglądarki | Research |
| Ustawienia regionalne | Ustawienia systemu serwera, cache, wstrzykiwalne | Testy niezależne od maszyny | Plan |
| Koniec wartości | Koniec linii lub przed znaną etykietą | Prosta reguła; nazwa łamana na 2 linie zostanie ucięta | Plan |
| Frontend | Minimalny: ostrzeżenia i format daty, test ręczny | E2E należy do fazy 3 | Plan |
| Konflikt etykiet jednego poziomu | Puste pole i ostrzeżenie | Nie podsuwa po cichu złej wartości | Plan |
| Język komunikatów | Angielski | Spójnie z istniejącym API | Plan |

## Scope

**In scope:**
- reguły etykiet i dat w ekstrakcji;
- `warranty_end_date_warnings`;
- `warnings` w odpowiedzi zapisu;
- zegar UTC;
- test przepływu korekty przez API;
- minimalne zmiany w `new.astro` i `api.ts`;
- aktualizacja §3 i §6 w test-plan.md.

**Out of scope:**
- e2e i testy scalania w przeglądarce;
- tłumaczenia;
- sklejanie wartości z wielu linii;
- blokowanie zapisu przez ostrzeżenia;
- bezpieczny zapis i odtwarzanie profilu (faza 2);
- remindery.

## Architecture / Approach

- Czyste funkcje (`_suggest_fields`, normalizacja dat, `warranty_end_date_warnings`) dostają podmienialne zależności: `date_order` i `utc_today()`, żeby testy jednostkowe nie zależały od maszyny.
- API zwraca `warnings: {field: message}` w tym samym kształcie co podgląd, a frontend je wyświetla.
- Szacunek i próg ostrzeżenia korzystają z jednej funkcji pomocniczej.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Poprawki ekstrakcji (test-first) | Reguły etykiet i dat z testami | Regex łamie istniejące przypadki OCR i embedded |
| 2. Zegar UTC i ostrzeżenia zapisu | `warnings` i deterministyczny status | Próg rozjeżdża się z szacunkiem |
| 3. Testy korekty przez API | Dowód, że zapisane są wartości poprawione | Mock podglądu zbyt luźny |
| 4. Minimalny frontend | Ostrzeżenia i format daty z przeglądarki | Reset formularza ukrywa ostrzeżenia |
| 5. Aktualizacja test-plan.md | §3 = done, cookbook §6 | Odwołania do nieistniejących testów |

**Prerequisites:** `uv` i zależności Pythona, `npm` we `frontend/`. Nie ma zmian schematu bazy.
**Estimated effort:** około 2–3 sesji w 5 fazach. Fazy 1 i 2 są największe.

## Open Risks & Assumptions

- Ustawienia regionalne bez rozpoznawalnego `%x` (np. ISO) dają domyślnie DMY.
- Granica dnia UTC oznacza świadomą różnicę: po północy czasu polskiego status może jeszcze przez 1–2 godziny bazować na wczorajszej dacie.
- Wymagane pola to product_name, purchase_date i purchase_type (roadmap.md:172-173). Shape-notes są w tym punkcie nieaktualne.

## Success Criteria (Summary)

- Każda reguła z decyzji właściciela ma test, który failuje po jej złamaniu.
- Użytkownik zapisuje nietypowy termin i widzi ostrzeżenie zamiast błędu.
- `uv run pytest -q` i `npm run build` przechodzą.
