---
project: PamiętajGwarancje
version: 1
status: draft
created: 2026-09-30
context_type: greenfield
product_type: web-app
target_scale:
  users: medium
  qps: TBD
  data_volume: TBD
timeline_budget:
  mvp_weeks: 3
  hard_deadline: null
  after_hours_only: true
---

## Vision & Problem Statement

Osoby prywatne posiadające narzędzia lub sprzęt nie mają łatwego podglądu, czy gwarancja nadal obowiązuje. Po awarii piły szablastej autor pomysłu musiał przeszukać segregator z dokumentami, by dopiero wtedy odkryć, że gwarancja wygasła; obecnym kosztem jest szukanie dokumentu i późne poznanie statusu.

Segregator przechowuje dokumenty, ale nie pokazuje od razu statusu gwarancji.

## User & Persona

### Primary persona

Autor pomysłu — osoba prywatna posiadająca narzędzia lub sprzęt. Sięga po informację o gwarancji, gdy sprzęt ulegnie awarii, i chce ją znaleźć bez przeszukiwania segregatora.

## Success Criteria

### Primary
- Użytkownik może dodać zakup ręcznie lub z PDF/OCR, poprawić odczytane dane i znaleźć zakup na ekranie głównym, który pokazuje gwarancje wkrótce wygasające i pozwala szukać po nazwie produktu.

### Secondary
- Użytkownik otrzymuje przypomnienie przed końcem gwarancji.

### Guardrails
- Ręczne poprawki danych odczytanych z dokumentu nie są tracone.

## User Stories

### US-01: Dodanie zakupu z PDF i sprawdzenie gwarancji

- **Given** użytkownik ma paragon lub fakturę w PDF
- **When** klika „+”, wybiera PDF, sprawdza i poprawia dane odczytane przez OCR, a następnie zapisuje zakup
- **Then** zakup pojawia się w aplikacji i można go znaleźć po nazwie produktu; jeśli gwarancja wkrótce wygasa, widać ją na ekranie głównym

#### Acceptance Criteria
- Dane odczytane z PDF można poprawić przed zapisaniem zakupu.
- Zapisany zakup można znaleźć po nazwie produktu.
- Gwarancja, która wkrótce wygasa, jest widoczna na ekranie głównym.

## Functional Requirements

### Dodawanie i edycja zakupów
- FR-001: Użytkownik może dodać zakup ręcznie. Priority: must-have
  > Socrates: Counter-argument considered: "PDF może być niedostępny lub nieczytelny." Resolution: kept; ręczne dodawanie pozostaje jako fallback.
- FR-002: Użytkownik może przechować paragon lub fakturę w PDF, a OCR odczytuje datę zakupu, miejsce lub sprzedawcę oraz sposób płatności. Priority: must-have
  > Socrates: Counter-argument considered: "OCR może błędnie odczytywać pola." Resolution: kept; OCR jest sednem pomysłu, a odczytane dane można poprawić.
- FR-003: Użytkownik może poprawić dane odczytane z PDF przed zapisaniem zakupu. Priority: must-have
  > Socrates: Brak kontrargumentu; wymaganie pozostaje bez zmian.
- FR-006: Użytkownik może edytować zapisany zakup. Priority: must-have
  > Socrates: Counter-argument considered: "Korekta przed zapisem może wystarczyć." Resolution: kept; później mogą być potrzebne zmiany w zapisanym zakupie.
- FR-007: Użytkownik może usuwać zapisany zakup lub dokument. Priority: must-have
  > Socrates: Counter-argument considered: "Usunięcie może pozbawić użytkownika dowodu zakupu." Resolution: kept; błędne lub zdublowane wpisy trzeba móc usunąć.

### Wyszukiwanie gwarancji
- FR-004: Użytkownik może zobaczyć na ekranie głównym gwarancje wkrótce wygasające. Priority: must-have
  > Socrates: Counter-argument considered: "Reguła daty i znaczenie 'wkrótce' nie są jeszcze ustalone." Resolution: kept; regułę trzeba doprecyzować osobno.
- FR-005: Użytkownik może wyszukiwać zakupy po nazwie produktu. Priority: must-have
  > Socrates: Counter-argument considered: "Przy małej liczbie zakupów wyszukiwanie po kategorii może poczekać." Resolution: kategorię odłożono; wyszukiwanie po nazwie pozostaje.

### Przypomnienia
- FR-008: Użytkownik może otrzymywać przypomnienie przed końcem gwarancji. Priority: nice-to-have
  > Socrates: Brak kontrargumentu; wymaganie pozostaje bez zmian jako nice-to-have.

## Non-Functional Requirements

- Treść faktur i odczytane z nich dane są widoczne wyłącznie dla właściciela profilu lub konta.
- Użytkownik otrzymuje wynik otwarcia ekranu głównego i wyszukiwania w ciągu 3 sekund.

## Business Logic

Aplikacja domyślnie wyznacza koniec gwarancji na dwa lata od daty zakupu prywatnego lub rok od daty zakupu firmowego, ale inny, w tym przedłużony, termin podany przez użytkownika na podstawie dokumentu zastępuje wartość domyślną.

Reguła wykorzystuje datę zakupu, rodzaj zakupu wybrany przez użytkownika oraz ewentualny inny lub przedłużony termin z dokumentu, który użytkownik może wpisać albo poprawić. Wynikiem jest data końca gwarancji i jej status; użytkownik widzi je w aplikacji, a gwarancje wkrótce wygasające także na ekranie głównym.

## Access Control

Na początku aplikacja ma lokalny profil. W przyszłości użytkownicy będą mieli konta, a każdy z nich dostęp wyłącznie do własnych dokumentów. Nie planuje się dodatkowych ról.

## Non-Goals

- OCR ze zdjęć nie należy do MVP; pierwsza wersja obsługuje dokumenty PDF.
- Współdzielenie zakupów i dokumentów nie należy do MVP; dane pozostają prywatne dla właściciela.
- Wyszukiwanie po kategorii nie należy do MVP; pierwsza wersja wyszukuje po nazwie produktu.
- Przypomnienia przed końcem gwarancji nie należą do MVP; są dodatkiem po głównym przepływie.
- Natywna aplikacja mobilna nie należy do MVP; pierwsza wersja jest webowa.

## Open Questions

1. **Które pola są obowiązkowe przy zapisie zakupu?** Owner: user.
2. **Jaki przedział czasu oznacza, że gwarancja wkrótce wygasa?** Owner: user.
3. **Jaki orientacyjny ruch i wolumen przechowywanych dokumentów należy zakładać?** Owner: user.
