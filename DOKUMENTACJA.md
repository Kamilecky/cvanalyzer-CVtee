# CVeeto — Dokumentacja użytkownika

> Wersja: 1.0 · Produkt dostępny pod adresem **cveeto.eu**

---

## Spis treści

1. [Co to jest CVeeto?](#1-co-to-jest-cveeto)
2. [Rejestracja i logowanie](#2-rejestracja-i-logowanie)
3. [Panel główny (Dashboard)](#3-panel-główny-dashboard)
4. [Zarządzanie CV](#4-zarządzanie-cv)
5. [Analiza CV](#5-analiza-cv)
6. [Dopasowanie do oferty pracy](#6-dopasowanie-do-oferty-pracy)
7. [Tryb HR — Rekrutacja](#7-tryb-hr--rekrutacja)
   - 7.1 [Stanowiska](#71-stanowiska)
   - 7.2 [Kandydaci](#72-kandydaci)
   - 7.3 [Dopasowanie kandydata do stanowisk](#73-dopasowanie-kandydata-do-stanowisk)
   - 7.4 [Ranking kandydatów (Position Ranks)](#74-ranking-kandydatów-position-ranks)
   - 7.5 [Szczegółowy wynik dopasowania](#75-szczegółowy-wynik-dopasowania)
   - 7.6 [Pytania rekrutacyjne AI](#76-pytania-rekrutacyjne-ai)
   - 7.7 [Candidate Intelligence](#77-candidate-intelligence)
8. [Bezpieczeństwo — ochrona przed manipulacją AI](#8-bezpieczeństwo--ochrona-przed-manipulacją-ai)
9. [Eksport raportu PDF](#9-eksport-raportu-pdf)
10. [Plany i subskrypcje](#10-plany-i-subskrypcje)
11. [Ustawienia konta](#11-ustawienia-konta)
12. [Najczęściej zadawane pytania (FAQ)](#12-najczęściej-zadawane-pytania-faq)

---

## 1. Co to jest CVeeto?

CVeeto to narzędzie oparte na sztucznej inteligencji, które pomaga w dwóch głównych obszarach:

**Dla kandydatów i osób szukających pracy:**
- Ocenia jakość Twojego CV i wskazuje słabe miejsca
- Sprawdza, jak bardzo Twoje CV pasuje do konkretnej oferty pracy
- Podpowiada, co poprawić, żeby zwiększyć szanse na rozmowę kwalifikacyjną

**Dla rekruterów i działów HR:**
- Automatycznie przetwarza CV kandydatów i tworzy ich ustrukturyzowane profile
- Dopasowuje kandydatów do otwartych stanowisk i tworzy ranking
- Generuje raport o każdym kandydacie (mocne strony, luki, rekomendacja: zaproszenie / do rozważenia / odrzucenie)
- Generuje propozycje pytań rekrutacyjnych dopasowanych do konkretnej osoby

Narzędzie działa w dwóch językach: **polskim i angielskim**.

---

## 2. Rejestracja i logowanie

### Rejestracja nowego konta

1. Wejdź na **cveeto.eu** i kliknij **„Zarejestruj się"**
2. Podaj adres e-mail i hasło
3. Na podany adres zostanie wysłany e-mail weryfikacyjny — kliknij link w wiadomości, aby aktywować konto
4. Po weryfikacji możesz się zalogować

> **Uwaga:** Bez weryfikacji adresu e-mail nie będzie możliwe korzystanie z systemu.

### Logowanie

Wpisz adres e-mail i hasło, które podałeś/aś podczas rejestracji.

### Zapomniałem/am hasła

Na stronie logowania kliknij **„Zapomniałem/am hasła"**, wpisz swój e-mail i postępuj zgodnie z instrukcją w wiadomości, która zostanie do Ciebie wysłana.

---

## 3. Panel główny (Dashboard)

Po zalogowaniu trafiasz na **Dashboard** — centrum sterowania aplikacją.

Znajdziesz tu:

| Element | Opis |
|---------|------|
| **Liczba analiz w tym miesiącu** | Ile analiz CV wykonałeś/aś w bieżącym miesiącu i jaki jest limit dla Twojego planu |
| **Ostatnie analizy** | Szybki dostęp do ostatnio przetworzonych CV |
| **Szybkie akcje** | Przyciski do przesłania CV, sprawdzenia historii analiz, przejścia do trybu HR |

W górnym menu znajdziesz nawigację do wszystkich sekcji serwisu.

---

## 4. Zarządzanie CV

### Przesyłanie CV

1. Kliknij **„Prześlij CV"** (przycisk w dashboardzie lub w menu)
2. Wybierz plik z dysku (obsługiwane formaty: **PDF, DOCX, DOC, TXT**)
3. Rozmiar pliku nie może przekraczać **10 MB**
4. Plik zostanie automatycznie przetworzony — tekst zostanie odczytany i zapisany w systemie

### Lista przesłanych CV

W zakładce **„CV"** znajdziesz wszystkie przesłane przez Ciebie dokumenty. Możesz:
- Podejrzeć szczegóły danego CV (plik, data przesłania, wykryty tekst)
- Usunąć CV, którego już nie potrzebujesz

> **Wskazówka:** System wykrywa zduplikowane pliki — jeśli prześlesz ten sam plik ponownie, nie zostanie on przetworzony podwójnie.

---

## 5. Analiza CV

To główna funkcja CVeeto dla osób szukających pracy lub chcących ocenić jakość swojego CV.

### Jak uruchomić analizę?

1. Przejdź do zakładki **„Analiza"**
2. Wybierz przesłane wcześniej CV lub prześlij nowe
3. Kliknij **„Analizuj"**
4. Poczekaj kilka sekund — zobaczysz pasek postępu
5. Po zakończeniu zostaniesz automatycznie przekierowany/a do raportu

### Co zawiera raport z analizy?

#### Podsumowanie
Krótki opis CV napisany przez AI — kim jest kandydat, jakie ma doświadczenie, co wyróżnia dokument.

#### Analiza sekcji
System sprawdza każdą sekcję CV (doświadczenie, wykształcenie, umiejętności, języki itd.) i ocenia ją jako:
- **Obecna** — sekcja istnieje i jest dobrze wypełniona
- **Słaba** — sekcja istnieje, ale wymaga uzupełnienia
- **Brakuje** — sekcja nie została wykryta

Do każdej sekcji dołączone są konkretne sugestie poprawy.

#### Problemy (zakładka „Problems")
Lista błędów i problemów znalezionych w CV, posortowanych według ważności:
- **Krytyczne** — poważne błędy, które mogą od razu dyskwalifikować CV
- **Ostrzeżenia** — rzeczy do poprawy
- **Informacje** — drobne uwagi

Każdy problem ma kategorię (np. formatowanie, treść, spójność) oraz opis dotkniętego fragmentu tekstu.

#### Rekomendacje *(plan Basic i wyższe)*
Konkretne wskazówki, co dodać lub zmienić w CV, żeby zwiększyć szanse na rozmowę. Każda rekomendacja ma priorytet (wysoki / średni / niski) i gotowy tekst do wklejenia.

#### Luki w umiejętnościach *(plan Basic i wyższe)*
Porównanie umiejętności kandydata z tym, czego oczekuje rynek pracy. Pokazuje:
- Jakiego poziomu brakuje (np. „Excel — aktualnie: podstawowy, zalecany: zaawansowany")
- Ważność danej umiejętności

#### Przepisywanie AI *(plan Premium i wyższe)*
AI przepisuje wybrane sekcje CV (np. podsumowanie zawodowe, opis doświadczenia) na lepszą, bardziej profesjonalną wersję. Widzisz obok siebie:
- Oryginalny tekst
- Ulepszony tekst
- Komentarz wyjaśniający, co i dlaczego zostało zmienione

Możesz zlecić przepisanie dowolnej sekcji przyciskiem **„Przepisz tę sekcję"**.

### Historia analiz

W zakładce **„Historia"** znajdziesz wszystkie poprzednie analizy. Możesz do nich wrócić w każdej chwili — wyniki są przechowywane na koncie.

> **Plan Basic i wyższe** — historia jest przechowywana bezterminowo.
> **Plan Free** — bieżące analizy dostępne, historia może być ograniczona.

---

## 6. Dopasowanie do oferty pracy

Ta funkcja pozwala sprawdzić, jak dobrze Twoje CV pasuje do **konkretnego ogłoszenia o pracę**.

### Jak to działa?

1. Przejdź do zakładki **„Dopasuj do oferty"**
2. Wybierz CV (lub prześlij nowe)
3. Wklej treść ogłoszenia o pracę (lub tytuł stanowiska + wymagania)
4. Kliknij **„Sprawdź dopasowanie"**
5. Poczekaj chwilę — AI porówna CV z ogłoszeniem

### Co pokazuje wynik?

| Element | Opis |
|---------|------|
| **Wynik dopasowania (%)** | Ogólna ocena — im wyższy, tym lepiej |
| **Pasujące umiejętności** | Umiejętności z CV, które pokrywają się z wymaganiami |
| **Brakujące umiejętności** | Czego wymaga pracodawca, a czego nie ma w CV |
| **Mocne strony** | Co w tym CV przemawia za kandydatem na to stanowisko |
| **Słabe strony** | Co może być problemem podczas rekrutacji |
| **Podsumowanie** | Krótkie zdanie AI: „Czy warto aplikować?" |

### Historia dopasowań

Możesz wracać do poprzednich dopasowań — system zapamiętuje, które CV sprawdzałeś/aś pod kątem jakich ofert.

---

## 7. Tryb HR — Rekrutacja

Tryb HR to osobny moduł dla **rekruterów i działów HR**. Dostępny jest na wszystkich planach (w tym Free — z limitem 3 stanowisk).

Wejdź do niego klikając **„Rekrutacja"** w górnym menu.

---

### 7.1 Stanowiska

Stanowisko to opis wolnego miejsca pracy, do którego będziesz dopasowywać kandydatów.

#### Tworzenie stanowiska

1. Kliknij **„Nowe stanowisko"**
2. Wypełnij formularz:
   - **Tytuł stanowiska** (np. „Specjalista ds. sprzedaży B2B")
   - **Dział** i **lokalizacja** (opcjonalnie)
   - **Typ zatrudnienia** (pełny etat / część etatu / kontrakt / zdalny / hybrydowy)
   - **Poziom seniority** (stażysta / junior / mid / senior / lead / principal)
   - **Wymagane umiejętności** — lista, jedna umiejętność w linii (np. „SAP — zaawansowany", „Excel")
   - **Dodatkowe umiejętności** — mile widziane, ale nieobowiązkowe
   - **Lata doświadczenia** (minimalne wymaganie)
   - **Opis obowiązków** — tekst z ogłoszenia
   - **Opis wymagań** — tekst z ogłoszenia
   - **Wymagane języki**
3. Kliknij **„Zapisz"**

> **Wskazówka dotycząca umiejętności:** Możesz wpisywać poziomy umiejętności bezpośrednio w nazwie, np. `Excel - zaawansowany` lub `Python - średniozaawansowany`. System automatycznie uwzględni poziom przy porównaniu z CV kandydatów.

#### Edycja i usuwanie stanowisk

Na liście stanowisk przy każdej pozycji znajdziesz przyciski edycji i usuwania.

#### Limity stanowisk wg planu

| Plan | Limit aktywnych stanowisk |
|------|--------------------------|
| Free | 3 |
| Basic | 10 |
| Premium | 50 |
| Enterprise | Bez limitu |

---

### 7.2 Kandydaci

Kandydat to osoba, której CV zostało przesłane do systemu i przetworzone na profil.

#### Przesyłanie CV kandydata

**Pojedynczy kandydat:**
1. Kliknij **„Prześlij CV"**
2. Wybierz plik i opcjonalnie przypisz od razu do stanowiska
3. System automatycznie przetworzy plik i wyekstrahuje informacje

**Wielu kandydatów naraz (Bulk Upload):**
1. Kliknij **„Bulk Upload"**
2. Wybierz wiele plików jednocześnie (max 10 MB każdy)
3. Wszystkie CV zostaną przetworzone równolegle

#### Co zostaje wyekstrahowane z CV?

System AI automatycznie odczytuje z CV:

| Informacja | Przykład |
|-----------|---------|
| Imię i nazwisko | Jan Kowalski |
| Adres e-mail | jan@example.com |
| Telefon | +48 600 000 000 |
| Lokalizacja | Warszawa |
| Obecne stanowisko | Senior Account Manager |
| Lata doświadczenia | 7 |
| Poziom seniority | Senior |
| Umiejętności | Python, Excel, SAP ERP... |
| Poziomy umiejętności | Python: zaawansowany, Excel: podstawowy |
| Wykształcenie | Mgr Zarządzania, UW, 2016 |
| Historia zatrudnienia | Firma, stanowisko, okres |
| Języki | Angielski, Niemiecki |
| Certyfikaty | PRINCE2, PMP... |
| Red flags | Luki w zatrudnieniu, częste zmiany pracy |
| Podsumowanie HR | Krótki opis kandydata dla rekrutera |
| Tagi | senior, sprzedaż, remote-ready... |

#### Lista kandydatów

Na stronie `/recruitment/candidates/` widzisz tabelę wszystkich kandydatów. Kolumny:
- Imię, rola, seniority, doświadczenie
- Umiejętności (pierwsze 5 + liczba pozostałych)
- Tagi
- **Intelligence** *(Premium/Enterprise)* — szybki badge z rekomendacją i wynikiem Skill Fit; po najechaniu myszą zobaczysz wyniki dopasowania do poszczególnych stanowisk
- Data dodania
- Akcje (podgląd, analiza CV, dopasowanie, usuń)

---

### 7.3 Dopasowanie kandydata do stanowisk

Po przesłaniu CV kandydata możesz go dopasować do stanowisk.

#### Opcja A — Dopasuj do wszystkich stanowisk

Na stronie kandydata kliknij **„Match to All Positions"**. System w tle dopasuje kandydata do każdego aktywnego stanowiska i stworzy wyniki.

#### Opcja B — Wybierz konkretne stanowiska

Kliknij **„Select Positions"**, zaznacz interesujące Cię stanowiska i kliknij **„Dopasuj"**.

#### Opcja C — Przypisz wielu kandydatów do stanowisk naraz (Bulk)

Na liście kandydatów kliknij **„Assign to Position"**, wybierz stanowiska i uruchom analizę zbiorczą.

#### Jak działa dopasowanie?

System porównuje profil kandydata ze stanowiskiem i oblicza:
- **Wynik ogólny (Overall Match %)** — ważona suma wszystkich kryteriów
- **Dopasowanie umiejętności (Skill Match %)** — ile wymaganych umiejętności kandydat posiada
- **Dopasowanie doświadczenia (Experience Match %)** — czy lata doświadczenia spełniają wymagania
- **Dopasowanie seniority** — czy poziom (junior/mid/senior itd.) pasuje
- **Dopasowanie wykształcenia**

**Ważna zasada dopasowania umiejętności:**
Jeśli stanowisko wymaga `Excel — zaawansowany`, a kandydat ma `Excel — bardzo zaawansowany`, umiejętność zostaje zaliczona jako **spełniona** (wyższy poziom niż wymagany = OK). Tylko jeśli kandydat ma niższy poziom niż wymagany, umiejętność pojawia się jako brakująca.

---

### 7.4 Ranking kandydatów (Position Ranks)

Strona `/recruitment/position-ranks/` to **centrum decyzyjne rekrutera** — widok wszystkich kandydatów ze wszystkich stanowisk z pełną kartą decyzyjną.

#### Filtry

Na górze strony znajdziesz dwa filtry:
- **Minimalny wynik dopasowania** — suwak (0–100%) — ukrywa kandydatów poniżej wybranego progu
- **Tylko krytyczne luki** — przełącznik — pokazuje tylko kandydatów z poważnymi brakami (do weryfikacji)

#### Karta kandydata

Każdy kandydat jest przedstawiony w osobnej karcie zawierającej:

**Nagłówek karty:**
- Numer w rankingu (medal dla #1)
- Imię i nazwisko
- Wynik dopasowania (%)
- Klasyfikacja: **Excellent / Strong / Moderate / Weak / Poor**

**Werdykt HR** (kolorowy pasek):
- **Zaproszenie na rozmowę** (zielony)
- **Do rozważenia** (żółty)
- **Niezalecany** (czerwony)

**Dlaczego kandydat #1?** *(tylko dla najlepszego kandydata)*
Krótkie zdanie wyjaśniające, co decyduje o pierwszym miejscu.

**Dopasowanie umiejętności:**
- Pasujące umiejętności — zielone, z podziałem na wymagane i opcjonalne
- Brakujące umiejętności — czerwone (wymagane) i pomarańczowe (opcjonalne)
- Legenda: **Important** (wymagane) / **Not important** (opcjonalne)

**Dopasowanie do obowiązków:**
- Obowiązki spełnione przez kandydata (zielone %)
- Obowiązki niespełnione (czerwone %)

**Stopka karty:**
- Wskaźnik pewności danych (Wysoka / Średnia / Niska — zależy od kompletności CV)
- Przycisk **„Match Breakdown"** — otwiera szczegółowy raport

---

### 7.5 Szczegółowy wynik dopasowania

Strona `/recruitment/fit/<id>/` pokazuje pełny raport dopasowania jednego kandydata do jednego stanowiska.

#### Ogólny wynik i klasyfikacja

Duży procent z kolorowym badge (Excellent / Strong / Moderate / Weak / Poor).

#### Analiza każdego wymagania (Requirement-by-Requirement)

Tabela z każdym wymaganiem ze stanowiska i odpowiadającym mu wynikiem dopasowania:
- Typ wymagania (wymagana umiejętność / opcjonalna umiejętność / obowiązek / doświadczenie / język)
- Wynik % z paskiem postępu
- Waga wymagania (jak bardzo wpływa na wynik ogólny)
- Wyjaśnienie AI (dlaczego taki wynik)

#### Analiza sekcji CV

Ocena każdej sekcji CV (Doświadczenie, Wykształcenie, Języki, Umiejętności, Zainteresowania) z:
- Wynikiem procentowym
- Wagą
- Komentarzem tekstowym

#### Rozbicie wyników

Cztery osobne karty: Skill Match, Experience Match, Seniority Match, Education Match — każda z paskiem postępu.

#### Pasujące i brakujące umiejętności

Dwie listy badge'ów: zielone (ma) i czerwone (brakuje).

#### Podsumowanie HR

Automatycznie generowany opis kandydata z perspektywy rekrutera.

#### Red Flags

Alerty dotyczące niepokoących sygnałów w CV (luki w zatrudnieniu, częste zmiany pracy, niespójności). Każdy flag ma poziom: **CRITICAL / WARNING / INFO**.

#### Pytania rekrutacyjne AI *(patrz sekcja 7.6)*

#### Candidate Intelligence *(patrz sekcja 7.7)*

---

### 7.6 Pytania rekrutacyjne AI

*(Dostępne w planie **Premium** i **Enterprise**)*

Na stronie szczegółowego wyniku dopasowania kliknij **„Generate AI Questions"**, aby otrzymać zestaw 5–8 pytań rekrutacyjnych dopasowanych do **konkretnego kandydata i konkretnego stanowiska**.

Każde pytanie zawiera:
- **Kategorię:** techniczna / behawioralna / sytuacyjna / kulturowa
- **Treść pytania**
- **Dlaczego warto zadać** — wyjaśnienie, co to pytanie ma zweryfikować (np. lukę w umiejętnościach, konkretne doświadczenie)

Pytania są spersonalizowane — AI analizuje historię zatrudnienia, brakujące umiejętności i profil kandydata, zamiast generować pytania ogólne.

---

### 7.7 Candidate Intelligence

*(Dostępne w planie **Premium** i **Enterprise**)*

Candidate Intelligence to pogłębiony raport AI o kandydacie, niezależny od konkretnego stanowiska. Pokazuje, kim jest kandydat jako osoba, a nie tylko czy spełnia wymagania.

#### Gdzie jest dostępny?

- Na stronie szczegółowego wyniku dopasowania `/recruitment/fit/<id>/`
- Na stronie profilu kandydata `/recruitment/candidates/<id>/`
- Skrócony podgląd (badge + hover) na liście kandydatów `/recruitment/candidates/`

#### Jak wygenerować?

**Dla nowych kandydatów:** Raport generuje się automatycznie w tle po zakończeniu ekstrakcji profilu.

**Dla istniejących kandydatów:** Kliknij przycisk **„Generate Intelligence Report"** na stronie kandydata lub na stronie wyniku dopasowania.

#### Co zawiera raport?

**Rekomendacja ogólna:**
Jedna z trzech decyzji AI:
- ✅ **Invite to Interview** — kandydat wart zaproszenia
- ➖ **Worth Considering** — warto rozważyć, ale są zastrzeżenia
- ❌ **Not Recommended** — poważne czerwone flagi lub zbyt duże luki

Wraz z krótkim uzasadnieniem dlaczego.

**Pewność danych:**
- **Wysoka** — CV jest szczegółowe i kompletne
- **Średnia** — CV częściowo wypełnione
- **Niska** — CV bardzo skąpe, wyniki mogą być nieprecyzyjne

**Skill Fit (Dopasowanie umiejętnościowe):**
- Wynik 0–100%
- Mocne umiejętności kandydata (zielone badge)
- Luki w umiejętnościach (czerwone badge)
- Jedno-zdaniowe podsumowanie

**Learning Potential (Potencjał do nauki):**
- Wynik 0–100%
- Sygnały z CV uzasadniające ocenę (np. „W ciągu 1 roku przeszedł z Javy na Pythona", „5 różnych technologii w 3 projektach")

**Career Trajectory (Ścieżka kariery):**
- **Ascending** — wyraźna progresja, awanse
- **Lateral** — ruchy poziome, zmiana branży bez awansu
- **Stagnant** — brak wzrostu przez długi czas
- **Early Career** — mniej niż 3 lata doświadczenia

**Behavioral Signals (Sygnały behawioralne):**
Lista 2–5 obserwacji o kandydacie, oznaczonych jako:
- 🟢 Pozytywne (np. „Konsekwentnie awansował w tej samej firmie")
- 🔴 Negatywne (np. „Trzy prace po 6 miesięcy z rzędu")
- ⚪ Neutralne

**Risk Flags (Flagi ryzyka):**
Najpoważniejsze zastrzeżenia z oceną: **High / Medium / Low**. Wyświetlane tylko jeśli AI wykryło realne powody do niepokoju.

#### Podgląd na liście kandydatów

W kolumnie **Intelligence** na liście kandydatów widzisz skrót:
- Kolorowy badge z rekomendacją (Invite / Consider / Reject)
- Po najechaniu myszą na **„Skill Fit X%"** — lista stanowisk, do których kandydat był dopasowany, z ich wynikami (zielony ≥75%, żółty ≥50%, czerwony <50%)

---

## 8. Bezpieczeństwo — ochrona przed manipulacją AI

CVeeto zawiera wbudowany system wykrywania **prompt injection** — prób manipulacji systemem AI poprzez złośliwą treść ukrytą w CV.

### Co to jest prompt injection?

Niektóre osoby mogą ukryć w CV niewidoczne instrukcje (np. białym tekstem na białym tle lub w metadanych), które próbują oszukać AI, by dało kandydatowi wyższe oceny niż na to zasługuje.

### Jak CVeeto się broni?

#### Detekcja

System automatycznie skanuje każde przesłane CV. Jeśli wykryje podejrzaną treść:
- CV zostaje **oflagowane** (oznaczone jako podejrzane)
- Kandydat znika z listy aktywnych kandydatów
- W panelu HR pojawia się **ostrzeżenie modalne** z listą oflagowanych CV

Każda flaga zawiera:
- Typ ataku (np. `hidden_text`, `instruction_injection`, `role_override`)
- Poziom ryzyka: **HIGH / MEDIUM / LOW**
- Fragment podejrzanej treści

#### Co możesz zrobić z oflagowanym CV?

Na stronie `/recruitment/flagged-cvs/` możesz:
- **Odrzucić alert** — jeśli uznajesz, że to fałszywy alarm, możesz odblokować kandydata
- **Przywrócić CV** — jeśli odrzuciłeś/aś alert przez pomyłkę
- **Odrzucić wszystkie alerty** naraz

#### Ochrona przed ukrytym prompt injection *(Premium i Enterprise)*

Bardziej zaawansowana warstwa ochrony wykrywająca ukryte instrukcje w formatowaniu dokumentu, metadanych pliku i niewidocznych znakach.

---

## 9. Eksport raportu PDF

*(Dostępne w planie **Premium** i **Enterprise**)*

Na stronie wyników analizy CV kliknij przycisk **„Export PDF"** (ikona dokumentu w prawym górnym rogu). System wygeneruje profesjonalny raport w formacie PDF zawierający:
- Podsumowanie CV
- Wyniki punktowe
- Listę problemów
- Rekomendacje
- Luki w umiejętnościach

Raport możesz pobrać na dysk lub przesłać kandydatowi.

---

## 10. Plany i subskrypcje

CVeeto oferuje cztery plany. Możesz zmienić plan w zakładce **„Billing"** w menu.

### Porównanie planów

| Funkcja | Free | Basic | Premium | Enterprise |
|---------|:----:|:-----:|:-------:|:----------:|
| Analizy miesięcznie | 15 | 50 | 300 | Bez limitu |
| Aktywne stanowiska HR | 3 | 10 | 50 | Bez limitu |
| Podstawowa ocena CV | ✅ | ✅ | ✅ | ✅ |
| Wykrywanie sekcji | ✅ | ✅ | ✅ | ✅ |
| Wykrywanie problemów | ✅ | ✅ | ✅ | ✅ |
| Dopasowanie do ofert | ✅ | ✅ | ✅ | ✅ |
| Tryb HR / Rekrutacja | ✅ | ✅ | ✅ | ✅ |
| Ranking kandydatów | ✅ | ✅ | ✅ | ✅ |
| Rekomendacje | ❌ | ✅ | ✅ | ✅ |
| Analiza luk w umiejętnościach | ❌ | ✅ | ✅ | ✅ |
| Wersjonowanie CV | ❌ | ✅ | ✅ | ✅ |
| Historia analiz | ❌ | ✅ | ✅ | ✅ |
| Eksport PDF | ❌ | ❌ | ✅ | ✅ |
| Przepisywanie AI | ❌ | ❌ | ✅ | ✅ |
| Pytania rekrutacyjne AI | ❌ | ❌ | ✅ | ✅ |
| Ocena wymagań | ❌ | ❌ | ✅ | ✅ |
| Benchmarking | ❌ | ❌ | ✅ | ✅ |
| Doradca kariery | ❌ | ❌ | ✅ | ✅ |
| **Candidate Intelligence** | ❌ | ❌ | ✅ | ✅ |
| Ochrona przed prompt injection | ❌ | ❌ | ✅ | ✅ |
| Priorytetowe przetwarzanie | ❌ | ❌ | ❌ | ✅ |
| Gwarancja SLA | ❌ | ❌ | ❌ | ✅ |
| **Cena miesięczna** | **0 zł** | **79 zł** | **199 zł** | **999 zł** |

### Jak kupić subskrypcję?

1. Przejdź do **„Billing" → „Pricing"** w menu
2. Wybierz plan i kliknij **„Upgrade"**
3. Zostaniesz przekierowany/a do bezpiecznej bramki płatności **Stripe**
4. Po opłaceniu subskrypcja jest aktywowana natychmiast
5. Otrzymasz e-mail potwierdzający aktywację

### Jak anulować subskrypcję?

1. Przejdź do **„Billing" → „Subscription"**
2. Kliknij **„Cancel Current Subscription"**
3. Potwierdź — wrócisz do planu Free

### Zmiana planu

Żeby przejść z jednego płatnego planu na inny:
1. Najpierw anuluj aktualną subskrypcję
2. Poczekaj, aż status zmieni się na Free
3. Wybierz nowy plan i opłać go

---

## 11. Ustawienia konta

W zakładce **„Profil"** (ikona osoby w górnym menu) możesz:

### Zmiana hasła

1. Kliknij **„Zmień hasło"**
2. Podaj obecne hasło, a następnie nowe (dwa razy)
3. Zapisz

### Zmiana adresu e-mail

1. Kliknij **„Zmień e-mail"**
2. Podaj nowy adres
3. Na nowy adres zostanie wysłany e-mail weryfikacyjny
4. Kliknij link w wiadomości — zmiana zostaje potwierdzona

### Tryb ciemny

W prawym górnym rogu znajdziesz przełącznik trybu jasny / ciemny. Ustawienie jest zapamiętywane w przeglądarce.

### Język interfejsu

Interfejs obsługuje **język polski i angielski**. Zmień język klikając odpowiednią opcję w menu językowym.

---

## 12. Najczęściej zadawane pytania (FAQ)

**Q: Ile czasu trwa analiza CV?**
A: Zazwyczaj 10–30 sekund. W godzinach szczytu może to potrwać do minuty. Pasek postępu na ekranie pokazuje aktualny status.

**Q: Jakie formaty plików są obsługiwane?**
A: PDF, DOCX, DOC, TXT. Rekomendujemy **PDF** — jest odczytywany najdokładniej.

**Q: Dlaczego moje CV ma niski wynik?**
A: System ocenia CV pod kątem kompletności, czytelności dla systemów ATS i zawartości merytorycznej. Najczęstsze powody niskiego wyniku: brakujące sekcje, zbyt mało treści, brak słów kluczowych dopasowanych do branży.

**Q: Czy moje CV jest bezpieczne?**
A: Tak. Pliki są przechowywane na bezpiecznych serwerach. Treść CV jest wysyłana do API OpenAI wyłącznie w celu analizy, zgodnie z polityką prywatności.

**Q: Dlaczego kandydat zniknął z listy?**
A: Prawdopodobnie jego CV zostało oflagowane jako podejrzane (prompt injection). Sprawdź sekcję **„Flagged CVs"** w module Rekrutacja.

**Q: Wynik dopasowania jest niski, ale kandydat wydaje się odpowiedni — co zrobić?**
A: Wynik AI to punkt wyjścia, nie wyrok. Sprawdź zakładkę szczegółów dopasowania — tam zobaczysz, co konkretnie AI uznało za brakujące i dlaczego. Możesz też uzupełnić opis stanowiska o synonimy używane przez kandydata.

**Q: Czy limity analiz resetują się co miesiąc?**
A: Tak, 1. dnia każdego miesiąca o północy.

**Q: Czy Candidate Intelligence bierze pod uwagę konkretne stanowisko?**
A: Nie — Candidate Intelligence to ogólna ocena kandydata jako osoby (potencjał, ścieżka kariery, sygnały behawioralne), niezależna od stanowiska. Wyniki dopasowania do konkretnych stanowisk znajdziesz w sekcji „Position Matches" na stronie kandydata.

**Q: Jaka jest różnica między planem Basic a Premium?**
A: Basic dodaje rekomendacje, analizę luk i historię. Premium dodaje eksport PDF, przepisywanie AI, pytania rekrutacyjne, ocenę wymagań i **Candidate Intelligence**. Pełne porównanie w tabeli w sekcji 10.

**Q: Czy mogę przetestować Premium przed zakupem?**
A: Plan Free jest dostępny bezterminowo i pozwala zapoznać się z podstawowymi funkcjami. Nie ma okresu próbnego Premium, ale możesz anulować subskrypcję w dowolnym momencie.

---

*Dokumentacja opracowana dla CVeeto v1.0 · cveeto.eu*
