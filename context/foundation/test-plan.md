# Test Plan

> Wielofazowy plan wdrażania testów. Strategia jest zamrożona w sekcjach §1–§5; wzorce w §6 będą uzupełniane w miarę realizacji faz.
> Przeczytaj przed dodaniem nowego testu.
>
> Odśwież: uruchom `/10x-test-plan --refresh`, gdy plan się zestarzeje (patrz §8).
>
> Ostatnia aktualizacja: 2026-10-13

## 1. Strategy

Testy w tym projekcie obowiązują trzy zasady:

1. **Cost × signal.** Najtańszy test, który daje wiarygodny sygnał dla danego ryzyka, ma pierwszeństwo. Nie wybieraj e2e tylko dlatego, że „wydaje się bezpieczniejsze”. Nie dodawaj testu wizualnego, jeśli prostsza asercja deterministycznie wykrywa tę samą regresję.
2. **User concerns are first-class evidence.** Obawy i wcześniejsze incydenty użytkownika mają taką samą wagę jak wymagania PRD i sygnały z historii zmian.
3. **Risks are scenarios, not code locations.** This plan documents *what could fail* and *why we believe it's likely* — drawn from documents, interview, and codebase *signal* (churn, structure, test base). It does NOT claim to know which line owns the failure. That knowledge is produced by `/10x-research` during each rollout phase. If the plan and research disagree about where the failure lives, research is the ground truth.

Zakres hot-spot scan: `src/warranties_10xdev/`, `frontend/src/`; wykluczono testy, dokumentację, archiwum i artefakty generowane.

## 2. Risk Map

Poniższe scenariusze są uporządkowane według wpływu i prawdopodobieństwa. Źródła wskazują dowody, które podniosły ryzyko, nie lokalizację usterki.

| # | Risk (failure scenario) | Impact | Likelihood | Source (evidence — not anchor) |
|---|---|---|---|---|
| 1 | Import PDF pomija lub błędnie rozpoznaje dane, a użytkownik nie może uzupełnić braków, zachować korekty i zapisać poprawnego zakupu. | High | High | PRD FR-002/003 i guardrail; wywiad Q1–Q4; `src/warranties_10xdev/` (9 commitów/30 dni), `frontend/src/pages/` (6) |
| 2 | Po błędzie zapisu metadane i PDF pozostają niespójne albo użytkownik traci skorygowany zakup. | High | Medium | PRD guardrail (linia 39); wywiad Q4; archiwalny plan PDF (linie 115–141) |
| 3 | Nieprawidłowy lub nadmiernie duży PDF omija walidację, ujawnia prywatne dane albo nadmiernie obciąża aplikację. | High | Medium | PRD prywatność (linia 80); archiwalny plan PDF (linie 71–79) |
| 4 | Data lub status gwarancji jest błędny przy zmianie rodzaju zakupu, ręcznym terminie albo granicy daty. | High | Medium | PRD Business Logic (linie 85–87); roadmap S-02 (linie 94–104) |
| 5 | Backup/restore odtwarza niespójny profil albo uszkadza istniejący profil przy nieprawidłowym archiwum. | High | Low | Archiwalny plan F-01 (linie 39–45, 104–106); istniejący kontrakt i testy odzyskiwania |
| 6 | Wyszukiwanie lub lista wygasających pomija właściwy zakup albo pokazuje zakup niepasujący do ustalonego kontraktu. | Medium | Medium | PRD FR-004/005; roadmap S-03 proposed i S-07 blocked, próg nieustalony (linie 106–116, 154–165) |

Wysoki wpływ i niskie prawdopodobieństwo ryzyka #6 nie uzasadnia rozbudowy testów chmurowych: istniejący zestaw odzyskiwania pozostaje gate'em, a odtworzenie należy okresowo sprawdzić operacyjnie. Przyjęto Low, ponieważ ten przepływ jest już wdrożony i osobno zweryfikowany, a historia zmian nie wskazuje go jako hot spotu.

### Risk Response Guidance

| Risk | What would prove protection | Must challenge | Context `/10x-research` must ground | Likely cheapest layer | Anti-pattern to avoid |
|---|---|---|---|---|---|
| #1 | Niezależnie znane pola trafiają do edytowalnego szkicu, braki można uzupełnić, a zapis zachowuje dokładnie ręczną korektę. | OCR nie jest źródłem prawdy; podgląd nie może ponownie nadpisać edycji. | Ekstrakcja, mapowanie pól, stan formularza, ścieżka błędu i wymagane dane. | Unit + API integration | Kruche porównanie całego tekstu, prawdziwa faktura lub oracle skopiowany z implementacji. |
| #2 | Po ponownym otwarciu profilu zakup zawiera poprawione wartości i powiązany PDF; wymuszony błąd nie zostawia połowy zapisu. | Sukces HTTP nie dowodzi trwałości ani spójności pliku i bazy. | Granice transakcji, blokada, kolejność operacji i punkty rollbacku. | Integration z tymczasowym profilem | Mockowanie bazy i plików zamiast sprawdzenia trwałego stanu. |
| #3 | Uszkodzony, nieczytelny i przekraczający limit PDF jest odrzucony bez zapisu, wycieku ścieżki ani pozostałego dokumentu. | Nie ufaj MIME type, nazwie pliku ani deklarowanemu rozmiarowi klienta. | Odczyt ograniczonych bajtów, granica renderowania/OCR, błędy i miejsce przechowywania. | API integration | Asercja samego statusu odpowiedzi bez efektów ubocznych i prywatności. |
| #4 | Niezależne przykłady reguł PRD dają właściwą datę, jej źródło i status na granicach. | Nie kopiuj oczekiwanej daty z bieżącego wyniku produkcyjnego obliczenia. | Wartości referencyjne PRD, semantyka dnia końcowego i deterministyczne „dziś”. | Unit | Test tautologiczny lub zależny od zegara systemowego. |
| #5 | Zweryfikowane archiwum odtwarza spójny profil, a uszkodzone/niebezpieczne nie zmienia celu. | Poprawna suma kontrolna nie dowodzi, że archiwum jest bezpieczne do aktywacji. | Format manifestu, walidacja ścieżek i punkt aktywacji odtworzenia. | Istniejąca integracja + okresowy manual restore smoke | Zależność od prawdziwych poświadczeń chmurowych lub test wyłącznie tworzenia archiwum. |
| #6 | Po uzgodnieniu kontraktu wyszukiwanie zwraca właściwe zakupy, a lista wygasających respektuje zatwierdzony przedział i cel 3 s. | Nie wymyślaj progu „wkrótce” ani nie zakładaj, że brak wyników oznacza brak pasujących danych. | Kontrakt S-03/S-07, źródła zakupów i statusów, decyzja właściciela o przedziale. | API integration + unit dla granic dat | Arbitralny próg, test tylko happy path lub niestabilny pomiar wydajności w CI. |

## 3. Phased Rollout

Każda faza otwiera osobny change folder przez `/10x-new`. Status przesuwa się przez stałe wartości parsera.

| # | Phase name | Goal (one line) | Risks covered | Test types | Status | Change folder |
|---|---|---|---|---|---|---|
| 1 | PDF and warranty contracts | Udowodnić poprawność importu, ręcznych korekt oraz reguł dat niezależnie od implementacji. | #1, #4 | pytest unit + API integration | not started | — |
| 2 | Safe persistence and recovery | Wykrywać niebezpieczne wejście, niespójny zapis oraz regresje odtwarzania profilu. | #2, #3, #5 | API/storage integration + manual restore smoke | not started | — |
| 3 | Critical browser flow | Sprawdzić pełny przepływ przesłanie–korekta–zapis bez utraty wartości. | #1, #2 | Playwright e2e | not started | — |
| 4 | Roadmap coverage and quality gates | Wymuszać bramki CI; dodać testy kontraktu search/dashboard w odpowiednich slice'ach, bez odblokowywania S-07 bez decyzji o progu. | #1–#6 | pytest + API integration + e2e + lint/typecheck/build gates | not started | — |

## 4. Stack

| Layer | Tool | Version | Notes |
|---|---|---|---|
| Unit + integration | pytest | 9.1.1 (`uv.lock`) | Sześć plików testowych wyłącznie w backendowym `tests/`; brak jawnej konfiguracji pytest. |
| API integration | FastAPI `TestClient` | Wersja przez FastAPI | Obecny wzorzec klienta testowego; używaj tymczasowych profili. |
| Astro build | Astro + TypeScript | 7.3.6 / 5.9.3 | Istnieje `build`; brak skryptu testów, testów frontendu i `astro check`. |
| Browser e2e | Playwright | Nie zainstalowano | Kandydat tylko dla krytycznego przepływu w fazie 3; nie zastępuje testów warstw niższych. |

**Klasyfikacja bazy testów:** `sparse` — sześć testów pytest zebranych w backendzie; brak frontendowego runnera i brak `.github/workflows/`.

**Stack grounding tools (current session):**
- Docs: Context7 — sprawdzono oficjalne Astro testing/TypeScript oraz pytest parametrization/fixtures; checked: 2026-10-13.
- Search: Exa dostępny, nieużyty — oficjalne dokumenty przez Context7 wystarczyły; checked: 2026-10-13.
- Runtime/browser: browser-control i Playwright execution dostępne w sesji — selektywny przegląd krytycznego ekranu, nie repozytoryjny runner; checked: 2026-10-13.
- Provider/platform: brak wykrytego provider MCP; stack hand-off wskazuje GitHub Actions, lecz workflow CI nie istnieje; checked: 2026-10-13.

Astro `build` nie wykonuje sprawdzania typów. W fazie 4 należy jawnie dodać i uruchamiać `astro check`; szczegóły integracji Vitest/Astro Container można ponownie zweryfikować w `/10x-research`, jeśli okaże się tańsza od testu przeglądarkowego.

## 5. Quality Gates

Obecnie nie ma workflow CI ani skryptu frontend test/typecheck. Faza 4 ma przypiąć poniższe bramki do rzeczywistych skryptów lokalnych i CI.

| Gate | Where | Required? | Catches |
|---|---|---|---|
| pytest unit + integration | Lokalnie + CI | required after §3 Phase 2 | Regresje ekstrakcji, walidacji, reguł domenowych i trwałego stanu. |
| Krytyczny browser e2e | CI na PR | required after §3 Phase 3 | Utrata wartości pomiędzy podglądem, edycją i zapisem. |
| Lint + typecheck | Lokalnie + CI | required after §3 Phase 4 | Błędy typów i niezgodność statyczna w Python/TypeScript. |
| Astro check + production build | Lokalnie + CI | required after §3 Phase 4 | Błędy diagnostyki Astro/TypeScript i niedziałający build. |
| Manual restore smoke | Operacyjnie przed wydaniem | recommended after §3 Phase 2 | Problemy środowiskowe niewidoczne w izolowanej integracji. |

Nie dodawaj snapshotów wizualnych ani multimodalnego gate'u dla wszystkich stron. Przegląd obrazu jest selektywny i ograniczony do krytycznego ekranu korekty.

## 6. Cookbook Patterns

Instrukcje dodawania testów w tym projekcie. Wzorce zostaną uzupełnione w końcowej podfazie odpowiedniego rollout'u.

### 6.1 Adding a unit test

- **Location**: `tests/`.
- **Naming**: `test_<behavior>.py`.
- **Reference test**: TBD — see §3 Phase 1 for PDF field extraction and correction behavior.
- **Run locally**: `uv run pytest tests/<test_file>.py`.

### 6.2 Adding an integration test

- **Location**: `tests/`.
- **Mocking policy**: Mockuj tylko zewnętrzne granice; sprawdzaj trwały stan przez tymczasowy profil.
- **Reference test**: TBD — see §3 Phase 2 for bounded PDF input, corrected-value persistence, and recovery.
- **Run locally**: `uv run pytest tests/<test_file>.py`.

### 6.3 Adding an e2e test

- **Location**: TBD — see §3 Phase 3 for the PDF preview, correction, and save flow.
- **Run locally**: TBD — see §3 Phase 3.

### 6.4 Adding a test for a new API endpoint

- **Test type**: API integration, unless research proves a cheaper layer gives the same signal.
- **Pattern**: TBD — see §3 Phase 2; assert response contract and persistent side effects.
- **Run locally**: `uv run pytest tests/<test_file>.py`.

## 7. What We Deliberately Don't Test

- **Detale wizualne poza krytycznymi ekranami** — nie dają proporcjonalnego sygnału dla obecnych ryzyk. Re-evaluate, jeśli ekran stanie się kluczowym produktem lub regresje wizualne będą miały istotny skutek. (Source: Phase 2 interview Q5.)
- **Przypomnienia o końcu gwarancji** — wykluczone z MVP; wrócić do testów po zmianie zakresu PRD. (Source: PRD Non-Goals, linia 98.)
- **OCR ze zdjęć i współdzielenie zakupów** — poza zakresem MVP; nie budować testów dla nieistniejących przepływów. (Source: PRD Non-Goals, linie 95–96.)
- **Testy S-03/S-07 przed gotowością slice'ów** — nie testować niezaimplementowanych przepływów; dla S-07 najpierw potrzebna jest decyzja właściciela o progu. (Source: roadmap S-03/S-07, linie 106–116, 154–165.)

## 8. Freshness Ledger

- Strategy (§1–§5) last reviewed: 2026-10-13
- Stack versions last verified: 2026-10-13
- AI-native tool references last verified: 2026-10-13 (no AI-native tool recommended)

Odśwież (`/10x-test-plan --refresh`), gdy:

- nowy risk z roadmapy lub archiwum znajdzie się w top 3,
- data `checked:` rekomendowanego narzędzia przekroczy trzy miesiące,
- zmieni się stack lub runner testów,
- uzgodniona sekcja §7 przestanie odpowiadać zakresowi produktu.
