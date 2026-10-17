# PDF and warranty contracts — plan implementacji

## Overview

Faza 1 z `context/foundation/test-plan.md` §3 (ryzyka #1 i #4). Naprawiamy cztery błędy ekstrakcji podpowiedzi z PDF i wprowadzamy reguły dat ustalone przez właściciela. Do tego dochodzą ostrzeżenia przy zapisie ręcznego terminu gwarancji oraz liczenie „dziś” w UTC. Każdą regułę zabezpieczamy testem, którego wyrocznią są decyzje właściciela, a nie obecny kod.

## Current State Analysis

- Ekstrakcja ([pdf_extraction.py](../../../src/warranties_10xdev/pdf_extraction.py)) to czyste funkcje `_suggest_fields` (:100), `_label_value` (:147) i `_normalize_date` (:163). Research odtworzył w nich 4 błędy:
  - ogólne `Date:` stojące przed `Purchase date:` wygrywa;
  - `Product-ID: 123` daje nazwę produktu `ID: 123`;
  - wartość wchłania kolejną linię z nieznaną etykietą (regex z `DOTALL`);
  - `DD-MM-YY` nie jest parsowane.
- Kolejność dzień/miesiąc jest zaszyta w kodzie (`%d.%m.%Y`, `%d-%m-%Y`) i nie zależy od ustawień systemu.
- `calculate_warranty` ([purchases.py](../../../src/warranties_10xdev/purchases.py):254) przyjmuje `today=`. API ([api.py](../../../src/warranties_10xdev/api.py):71) wywołuje ją bez tego parametru, więc status liczy się z lokalnego `date.today()`.
- Odpowiedź zapisu nie ma pola `warnings`. Ręczny termin przed datą zakupu jest dziś akceptowany po cichu.
- Frontend ([new.astro](../../../frontend/src/pages/purchases/new.astro):302-304) formatuje daty na sztywno w `pl-PL`. Typ `SavedPurchase` ([api.ts](../../../frontend/src/lib/api.ts):15) nie zna ostrzeżeń.
- Testy: `uv run pytest -q` daje 63 passed. Nie ma conftest. Wzorce to `TestClient(api.app)`, `tmp_path` przez `WARRANTIES_DATA_DIR`, ręcznie budowane PDF-y i monkeypatch.

## Desired End State

- Podpowiedzi z PDF spełniają reguły ekstrakcji z decyzji 1, 2 i 6 w research.md.
- Zapis zawsze się udaje, gdy wymagane pola są poprawne. Zwraca `warnings.warranty_end_date`, gdy ręczny termin jest przed zakupem albo później niż szacunek dla rodzaju zakupu.
- Status gwarancji w API liczy się od daty UTC, z możliwością podmiany zegara w testach.
- Frontend pokazuje ostrzeżenia zapisu i formatuje daty według ustawień przeglądarki.
- test-plan.md §3 i §6 wskazują tę zmianę i testy referencyjne.

Weryfikacja: `uv run pytest -q` przechodzi, nowe testy dla każdej reguły są zielone, a `npm run build` we `frontend/` kończy się sukcesem.

### Key Discoveries:

- `_FIELD_LABELS` (pdf_extraction.py:133) już miesza etykiety szczegółowe (wielowyrazowe: `purchase date`, `data zakupu`, `product name`) i ogólne (`date`, `data`, `product`, `payment`). Poziom szczegółowości można z tego wyprowadzić.
- Na Windows `locale.nl_langinfo` nie istnieje. Działa `setlocale(LC_TIME, "")` plus `strftime("%x")` na znanej dacie: dla Polish_Poland daje `05.03.2026`. `setlocale` zmienia stan całego procesu.
- Wzorzec `warnings: {pole: komunikat}` istnieje już w podglądzie (`PdfSuggestions.warnings`, `PreviewDraft.warnings`).
- API nie ma endpointu odczytu zakupu. Ponowne otwarcie w testach to odczyt z `profile.sqlite3`, tak jak w test_pdf_purchase_flow.py:82.

## What We're NOT Doing

- Testów logiki scalania w przeglądarce (nowy plik po edycji, nieaktualne podpowiedzi). To faza 3 test-planu (Playwright).
- Testów e2e i automatycznych testów UI. Zmiany frontendu w fazie 4 weryfikujemy ręcznie.
- Tłumaczenia komunikatów. Nowe ostrzeżenia są po angielsku, jak istniejące.
- Sklejania nazwy produktu łamanej na 2 linie. Świadomy kompromis: wartość kończy się na końcu linii.
- Blokowania zapisu przez ostrzeżenia dotyczące terminu ani zmian w zapisanym `warranty_end_date`.
- Zmian w progu ostrzeżenia poza szacunkiem dla rodzaju zakupu, czyli bez osobnego progu „2 lata”.
- Bezpiecznego zapisu i odtwarzania profilu (faza 2 test-planu) oraz reminderów.

## Implementation Approach

Najpierw czyste funkcje ekstrakcji, test-first, bo każdą regułę da się nazwać jednym zdaniem. Potem reguły gwarancji: osobna czysta funkcja ostrzeżeń oraz zegar UTC w API, z testami jednostkowymi i API. Następnie testy API przepływu korekty, który łączy podgląd z zapisem. Na końcu minimalny frontend i aktualizacja test-planu.

Wyrocznia dla wszystkich asercji to tabele decyzji w research.md (Follow-up 1 i 2), a nie wyniki obecnego kodu.

## Critical Implementation Details

- **Ustawienia regionalne:** kolejność dat odczytujemy raz i cache'ujemy. Wartość musi dać się wstrzyknąć parametrem, bez wywoływania `setlocale` w testach. Testy nie mogą zależeć od ustawień maszyny, na której działają.
- **Granica dnia UTC:** test API ustawia zegar na 2026-10-17 22:30 UTC, co odpowiada 2026-10-18 00:30 w Warszawie (CEST). Dla terminu 2026-10-17 oczekuje statusu `active`. To dokumentuje zaakceptowaną różnicę jednego dnia.

## Faza 1: Poprawki ekstrakcji (test-first)

### Overview

Testy jednostkowe `_suggest_fields` i normalizacji dat dla każdej reguły z decyzji 1, 2 i 6, potem minimalne poprawki.

### Changes Required:

#### 1. Testy ekstrakcji

**File**: `tests/test_pdf_extraction.py`

**Intent**: Dodać testy jednostkowe na tekście (bez budowania PDF), po jednym na regułę. Dla formatów dat użyć jednego testu parametryzowanego.

**Contract**: Wywołania `_suggest_fields(text, [], date_order=...)`. Przypadki (wyrocznia: research.md, decyzje 1, 2 i 6):
- `"Date: 2026-01-01\nPurchase date: 2026-03-05"` daje `purchase_date == "2026-03-05"`. Etykieta szczegółowa wygrywa niezależnie od pozycji.
- `"Product-ID: 123\nProduct name: Drill"` daje `"Drill"`. Samo `"Product-ID: 123"` daje `None` i ostrzeżenie.
- `"Product: Drill\nWarranty: 24 months"` daje `"Drill"`. Nieznana etykieta w kolejnej linii nie jest wchłaniana.
- `"Product: Drill Seller: Castorama"` daje `"Drill"` i `"Castorama"`. Wartość kończy się przed znaną etykietą w tej samej linii.
- `"Purchase date: 2026-03-05\nData zakupu: 2026-04-01"` daje `None` i ostrzeżenie o kilku różnych wartościach. Takie same wartości przy dwóch etykietach dają podpowiedź.
- Daty (parametryzowane, `date_order` `DMY` / `MDY`):
  - `2026-03-05` zawsze daje `2026-03-05`;
  - `05/03/2026` zawsze daje `2026-03-05`;
  - `05.03.2026` i `05-03-26` przy DMY dają `2026-03-05`, a przy MDY `2026-05-03`;
  - `31.02.2026` daje `None` i ostrzeżenie.
- Istniejące testy (embedded, OCR z `03.04.2025`, brakujące pola) zachowują swoje asercje. Jedyna zmiana: test OCR przekazuje `date_order="DMY"`, żeby nie zależeć od ustawień maszyny.

#### 2. Wykrywanie kolejności dat z ustawień systemu

**File**: `src/warranties_10xdev/pdf_extraction.py`

**Intent**: Odczytać raz z ustawień regionalnych serwera, czy dzień jest przed miesiącem, i umożliwić podmianę tej wartości w testach.

**Contract**: Funkcja `system_date_order() -> Literal["DMY", "MDY"]`, cache'owana. Używa `setlocale(LC_TIME, "")` i `strftime("%x")` na dacie 2026-03-05 (dzień ≠ miesiąc), a potem porównuje pozycję `05` i `03`. Gdy nie da się tego ustalić, zwraca `DMY`. `extract_pdf_suggestions` i `_suggest_fields` dostają argument `date_order: Literal["DMY", "MDY"] | None = None`, a `None` oznacza `system_date_order()`.

#### 3. Reguły etykiet i dat

**File**: `src/warranties_10xdev/pdf_extraction.py`

**Intent**: Wprowadzić szczegółowość etykiet, granicę linii, ochronę przed `Product-ID`, wykrywanie konfliktu i nowe formaty dat.

**Contract**:
- Etykiety dzielą się na szczegółowe (wielowyrazowe) i ogólne (jednowyrazowe). Pierwszeństwo mają szczegółowe; ogólne są używane tylko wtedy, gdy nie ma żadnej szczegółowej.
- Separator etykiety to `:` albo `-` otoczony białymi znakami. Etykieta, po której stoi `-` sklejony z wyrazem (np. `Product-ID`), nie jest etykietą.
- Wartość kończy się na `\n` albo przed znaną etykietą w tej samej linii (bez `DOTALL`).
- Konflikt: wszystkie dopasowania wybranego poziomu, po `strip()`. Jeśli są różne, pole dostaje `None` i ostrzeżenie `"Multiple different <field> values were found; enter it manually."`. Prefiks ostrzeżeń OCR zostaje jak dziś.
- Daty:
  - `YYYY-MM-DD` to rok-miesiąc-dzień;
  - `/` to zawsze dzień/miesiąc/rok;
  - `.` i `-` z rokiem na końcu (2 lub 4 cyfry) według `date_order`;
  - nieistniejąca data daje `None`.

### Success Criteria:

#### Automated Verification:

- Nowe testy ekstrakcji przechodzą: `uv run pytest tests/test_pdf_extraction.py`
- Testy podglądu w API nadal przechodzą: `uv run pytest tests/test_pdf_preview_api.py`
- Cały zestaw przechodzi: `uv run pytest -q`

#### Manual Verification:

- Każdy nowy test ma w nazwie lub komentarzu odwołanie do reguły, którą chroni (decyzja 1, 2 lub 6 z research.md)

**Implementation Note**: Po zielonej weryfikacji automatycznej zatrzymaj się na ręczne potwierdzenie przed fazą 2.

---

## Faza 2: Gwarancja — zegar UTC i ostrzeżenia zapisu

### Overview

Czysta funkcja ostrzeżeń dla ręcznego terminu, pole `warnings` w odpowiedzi zapisu i „dziś” w UTC w API. Testy jednostkowe i API.

### Changes Required:

#### 1. Ostrzeżenia terminu

**File**: `src/warranties_10xdev/purchases.py`

**Intent**: Wyznaczyć ostrzeżenia dla ręcznego terminu bez blokowania zapisu. Próg to ta sama data co szacunek w `calculate_warranty`.

**Contract**: `warranty_end_date_warnings(purchase: PurchaseInput) -> dict[str, str]`.
- Brak ręcznego terminu: `{}`.
- Termin wcześniejszy niż `purchase_date`: `{"warranty_end_date": "Warranty end date is earlier than the purchase date."}`.
- Termin późniejszy niż szacunek (prywatny: +2 lata, firmowy: +1 rok, 29 lutego → 28 lutego): `{"warranty_end_date": "Warranty end date is later than the estimated <N>-year <type> warranty (<YYYY-MM-DD>)."}`.
- Data równa progowi: brak ostrzeżenia.

Obliczanie szacunku wydzielamy do funkcji pomocniczej, z której korzystają obie ścieżki, żeby próg i szacunek nie mogły się rozjechać.

#### 2. Zegar UTC i ostrzeżenia w API

**File**: `src/warranties_10xdev/api.py`

**Intent**: Liczyć status od daty UTC i zwracać ostrzeżenia w odpowiedzi zapisu.

**Contract**:
- Funkcja modułu `utc_today() -> date` zwraca `datetime.now(timezone.utc).date()`; testy podmieniają ją przez monkeypatch.
- `save_purchase` wywołuje `calculate_warranty(purchase, today=utc_today())`.
- Odpowiedź zawiera zawsze `warnings: dict[str, str]`, czyli `{}`, gdy nie ma ostrzeżeń.
- Kody 422, 503, 500 i 413 bez zmian.

#### 3. Testy

**File**: `tests/test_warranty_calculation.py`, `tests/test_pdf_purchase_flow.py`

**Intent**: Zablokować regułę ostrzeżeń, deterministyczny status i granicę UTC.

**Contract**:
- Jednostkowe, parametryzowane (zakup 2026-03-10):
  - termin 2027-06-01 daje ostrzeżenie tylko dla `business`;
  - 2028-03-10 przy `private` i 2027-03-10 przy `business` nie dają ostrzeżenia (granica);
  - 2028-03-11 przy `private` daje ostrzeżenie;
  - 2026-03-09 daje ostrzeżenie „earlier”;
  - brak terminu daje `{}`;
  - zakup 2024-02-29 `business` z terminem 2025-03-01 daje ostrzeżenie z progiem 2025-02-28.
- API (zegar podmieniony):
  - zapis z terminem przed zakupem zwraca 200, zapisuje wiersz i ma `warnings.warranty_end_date`;
  - zakup `business` bez terminu ma `effective_end_date` = +1 rok, `date_basis == "estimate"`, a `warnings == {}`;
  - granica UTC: dla `utc_today` 2026-10-17 i terminu 2026-10-17 status to `active`; dla 2026-10-18 status to `expired`.
- Słaba asercja w test_pdf_purchase_flow.py:261 (`status in {...}`) zostaje zastąpiona dokładną wartością przy podmienionym zegarze.

### Success Criteria:

#### Automated Verification:

- Testy gwarancji przechodzą: `uv run pytest tests/test_warranty_calculation.py`
- Testy przepływu zapisu przechodzą: `uv run pytest tests/test_pdf_purchase_flow.py`
- Cały zestaw przechodzi: `uv run pytest -q`

#### Manual Verification:

- Ręczne wywołanie zapisu (np. `/docs` FastAPI) z terminem przed zakupem zwraca 200 i czytelne ostrzeżenie

**Implementation Note**: Po zielonej weryfikacji automatycznej zatrzymaj się na ręczne potwierdzenie przed fazą 3.

---

## Faza 3: Testy korekty przez API

### Overview

Test przepływu podgląd → korekta → zapis → ponowne otwarcie. Dowodzi, że zapisywane są wartości poprawione przez użytkownika, a nie podpowiedzi.

### Changes Required:

#### 1. Test przepływu korekty

**File**: `tests/test_pdf_purchase_flow.py`

**Intent**: Połączyć podgląd (z zamockowanym `extract_pdf_suggestions`, który zwraca błędne podpowiedzi) z zapisem poprawionych pól. Potem odczytać wiersz z `profile.sqlite3`.

**Contract**: Parametryzowane przypadki:
- wszystkie cztery pola poprawione: zapisane są wartości z formularza, a nie z podglądu;
- nazwa z białymi znakami na brzegach jest zapisana po `strip()`;
- puste opcjonalne `seller` lub `payment_method` (sam `""` lub same spacje) są zapisane jako `NULL`, mimo że podgląd je podpowiedział;
- poprawiona data zakupu: zapisana jest data z formularza, a `effective_end_date` liczy się od niej.

Plik PDF jest zapisany prywatnie, z tym samym `document_ref` co w istniejących testach.

### Success Criteria:

#### Automated Verification:

- Test korekty przechodzi: `uv run pytest tests/test_pdf_purchase_flow.py`
- Cały zestaw przechodzi: `uv run pytest -q`

**Implementation Note**: Po zielonej weryfikacji przejdź do fazy 4.

---

## Faza 4: Minimalny frontend

### Overview

Pokazać ostrzeżenia zapisu i formatować daty według ustawień przeglądarki. Weryfikacja ręczna; e2e przyjdzie w fazie 3 test-planu.

### Changes Required:

#### 1. Typ odpowiedzi

**File**: `frontend/src/lib/api.ts`

**Intent**: Uwzględnić ostrzeżenia w typie odpowiedzi zapisu.

**Contract**: `SavedPurchase.warnings: Partial<Record<string, string>>`.

#### 2. Widok dodawania zakupu

**File**: `frontend/src/pages/purchases/new.astro`

**Intent**: Po udanym zapisie pokazać ostrzeżenia obok komunikatu sukcesu i formatować daty według ustawień przeglądarki.

**Contract**:
- `Intl.DateTimeFormat(undefined, { timeZone: "UTC", ... })` zamiast `"pl-PL"` (:302-304).
- Ostrzeżenia renderowane istniejącymi komponentami z `frontend/src/components/ui/` i tokenami z `tokens.css`, tak jak ostrzeżenia podglądu.
- Reset formularza po sukcesie (:327-332) nie ukrywa ostrzeżeń, zanim użytkownik je zobaczy.

### Success Criteria:

#### Automated Verification:

- Build frontendu przechodzi: `npm run build` w `frontend/`

#### Manual Verification:

- Zapis z terminem przed zakupem pokazuje ostrzeżenie, a zakup jest zapisany
- Data w podsumowaniu zapisu ma format zgodny z ustawieniami przeglądarki (np. `en-US` daje M/D/YYYY)
- Stany na `frontend/src/pages/purchases/new-states.astro` nadal wyglądają poprawnie

**Implementation Note**: Po weryfikacji ręcznej przejdź do fazy 5.

---

## Faza 5: Aktualizacja test-plan.md

### Overview

Zapisać wynik fazy rolloutu i testy referencyjne w cookbooku.

### Changes Required:

#### 1. Rollout i cookbook

**File**: `context/foundation/test-plan.md`

**Intent**: Oznaczyć fazę 1 jako zrobioną i wskazać testy referencyjne.

**Contract**:
- W §3 wiersz 1: Status `done`, Change folder `context/changes/pdf-and-warranty-contracts/`.
- W §6.1 „Reference test”: test parametryzowany dat z `tests/test_pdf_extraction.py` oraz ostrzeżeń z `tests/test_warranty_calculation.py`.
- W §6.4 „Pattern”: test UTC lub ostrzeżeń w API z `tests/test_pdf_purchase_flow.py` (podmiana `utc_today`, asercja kontraktu i wiersza w bazie).
- Pozostałe wpisy TBD zostają.

### Success Criteria:

#### Automated Verification:

- Cały zestaw przechodzi: `uv run pytest -q`

#### Manual Verification:

- §3 i §6 wskazują istniejące pliki i nazwy testów

---

## Testing Strategy

### Unit Tests:

- `_suggest_fields` i normalizacja dat: szczegółowość etykiet, `Product-ID`, granica linii, konflikt, formaty dat przy DMY i MDY, nieistniejąca data.
- `warranty_end_date_warnings`: granica progu, rodzaj zakupu, 29 lutego, termin przed zakupem.

### Integration Tests:

- API zapisu: ostrzeżenia nie blokują zapisu, szacunek dla zakupu firmowego, granica dnia UTC przy podmienionym zegarze.
- Podgląd → korekta → zapis → odczyt z bazy.

### Manual Testing Steps:

1. Zapisać zakup z terminem przed datą zakupu i sprawdzić, że widać ostrzeżenie, a zakup jest zapisany.
2. Zmienić język przeglądarki na `en-US` i sprawdzić format daty.
3. Przejrzeć `new-states.astro`.

## Performance Considerations

Odczyt ustawień regionalnych jest cache'owany, więc jest jeden na proces.

## Migration Notes

Brak zmian schematu. Nowe pole `warnings` w odpowiedzi jest addytywne.

## References

- Research: `context/changes/pdf-and-warranty-contracts/research.md` (decyzje: Follow-up 1 i 2)
- Test plan: `context/foundation/test-plan.md` §3, §6
- Wymagane pola: `context/foundation/roadmap.md:172-173`
- Wzorzec ostrzeżeń: `src/warranties_10xdev/pdf_extraction.py:100`, `frontend/src/lib/api.ts:7`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Poprawki ekstrakcji (test-first)

#### Automated

- [x] 1.1 Nowe testy ekstrakcji przechodzą: `uv run pytest tests/test_pdf_extraction.py` — 601a743
- [x] 1.2 Testy podglądu w API nadal przechodzą: `uv run pytest tests/test_pdf_preview_api.py` — 601a743
- [x] 1.3 Cały zestaw przechodzi: `uv run pytest -q` — 601a743

#### Manual

- [x] 1.4 Każdy nowy test ma w nazwie lub komentarzu odwołanie do reguły, którą chroni (decyzja 1, 2 lub 6 z research.md) — 601a743

### Phase 2: Gwarancja — zegar UTC i ostrzeżenia zapisu

#### Automated

- [x] 2.1 Testy gwarancji przechodzą: `uv run pytest tests/test_warranty_calculation.py` — b705c82
- [x] 2.2 Testy przepływu zapisu przechodzą: `uv run pytest tests/test_pdf_purchase_flow.py` — b705c82
- [x] 2.3 Cały zestaw przechodzi: `uv run pytest -q` — b705c82

#### Manual

- [x] 2.4 Ręczne wywołanie zapisu (np. `/docs` FastAPI) z terminem przed zakupem zwraca 200 i czytelne ostrzeżenie — b705c82

### Phase 3: Testy korekty przez API

#### Automated

- [x] 3.1 Test korekty przechodzi: `uv run pytest tests/test_pdf_purchase_flow.py` — 174c3f8
- [x] 3.2 Cały zestaw przechodzi: `uv run pytest -q` — 174c3f8

### Phase 4: Minimalny frontend

#### Automated

- [x] 4.1 Build frontendu przechodzi: `npm run build` w `frontend/`

#### Manual

- [x] 4.2 Zapis z terminem przed zakupem pokazuje ostrzeżenie, a zakup jest zapisany
- [x] 4.3 Data w podsumowaniu zapisu ma format zgodny z ustawieniami przeglądarki (np. `en-US` daje M/D/YYYY)
- [x] 4.4 Stany na `frontend/src/pages/purchases/new-states.astro` nadal wyglądają poprawnie

### Phase 5: Aktualizacja test-plan.md

#### Automated

- [ ] 5.1 Cały zestaw przechodzi: `uv run pytest -q`

#### Manual

- [ ] 5.2 §3 i §6 wskazują istniejące pliki i nazwy testów
