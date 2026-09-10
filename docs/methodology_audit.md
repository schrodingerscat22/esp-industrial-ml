# Audyt metodologii ESP — 2026-09-10

## Stan i ochrona danych

Punkt wyjścia: commit `bfaa9bb`, lokalny `main`, repozytorium
`schrodingerscat22/esp-industrial-ml`. Początkowy `git status --short` był pusty.
Nie znaleziono instrukcji AGENTS.md w repozytorium ani sprawdzonych katalogach
nadrzędnych. Praca na gałęzi `codex/methodology-audit`; bez commitowania i push.
Dane raw, interim i processed są ignorowane przez Git; `git ls-files data` był pusty.
Istnieją cztery archiwa surowe ZIP, scalony parquet i przetworzone dane, w tym
`dataset_clean.parquet` i `df_model_clean_v1.parquet` oraz metadane tagów.
Audyt używa istniejących danych przetworzonych, nie odtwarza ekstrakcji ZIP.
Pochodzenie i kompletność wcześniejszego czyszczenia nie są jeszcze potwierdzone.

Skrypt `scripts/run_methodology_audit.py` zapisuje tylko w `data/processed/audit_v2`.
Sprawdza SHA-256 wszystkich istniejących plików danych przed i po przeliczeniu.
Manifest, szczegółowe wyniki i logi pozostają lokalne. Wyczyszczono outputy
zmienionych notebooków, aby nie mieszać dawnych wyników z poprawionym kodem
i nie dodawać nowych danych przemysłowych do śledzonych plików.
Historyczne outputy w niezmienionych notebookach i historii Git wymagają
osobnego przeglądu przed jakąkolwiek przyszłą publikacją; historii nie przepisywano.

## Potwierdzone błędy kodu i naprawy

1. **01, pierwotna komórka 20:** `rolling(30).mean()` dla targetu zawierało `y(t)`
   w predyktorze `y(t)`. Zastąpiono pełną średnią z `[t−5 min,t)`, zerując historię
   na granicach ciągłych segmentów. Opóźnienia napięć również nie przechodzą przez
   luki. Wejście wskazano jawnie (`dataset_clean.parquet`) zamiast pierwszego
   pliku z glob. Średnia na wykresie EDA nie była sama w sobie przeciekiem modelu.
   Obecny eksperyment jest online nowcastingiem z dostępem do przeszłego pyłomierza,
   a nie dowodem skuteczności predykcji bez tego czujnika ani prognozą wielokrokową.
2. **06a, pierwotna komórka 6:** gałąź ujemnego lagu dawała tę samą relację co
   dodatni lag o tej samej wartości bezwzględnej. Jedna definicja:
   `corr(x(t), y(t+lag))`, dodatni lag = x poprzedza y. Realizacja przesuwa y o
   `−lag` wewnątrz ciągłych segmentów. Każdy lag raportuje własne n par.
3. **04 i 06a:** okna z `iloc` mogły obejmować luki i przypisywać próbkom fałszywy
   czas względny. Teraz wymagany jest pełny ciąg znaczników co 10 s i skończone
   wartości wszystkich analizowanych sygnałów. Brakujące/ucięte okno jest odrzucane,
   bez interpolacji. Rapping: okna statystyk są półotwarte; dodatkowo wymagamy
   ciągłości od startu do prawej granicy. Profile mają oba końce do rysowania.
   ECO raportuje odrzucenia niepełne i nakładające się; wyklucza inne starty tego
   samego tagu w odległości mniejszej niż 15 min. To nie wyklucza innych strzepywaczy.
4. **Start i czas od rappingu:** wymagane obserwowane 0→1 w odstępie 10 s.
   Nie tworzymy startu przez lukę. Czas od startu oparty na timestampach, nie liczbie
   wierszy; po luce i przed pierwszym startem stan okna jest nieznany przez 5 min.
   Znany brak okna = −1, stan nieznany = NaN. 05 i 06b przeliczają cechy z sygnału
   wejściowego i wykluczają stan nieznany zamiast traktować go jako emisję bazową.
   06b używa również różnic napięcia ograniczonych do ciągłych segmentów;
   częstości przekroczeń różnic wykluczają NaN z mianownika.
5. **04, prawdopodobieństwa:** NaN maksimum było traktowane jak nieprzekroczenie.
   Mianownik obejmuje teraz tylko pełne, dostępne okna.
6. **04, zapisy:** nowe artefakty powstają w `audit_v2`, bez nadpisania v1.
   Usunięto ręcznie wpisane historyczne metryki z porównania modeli; ta część nadal
   wymaga wspólnego podziału treningowego i ponownego feature engineering 02/03.

Numery powyżej odnoszą się do komórek sprzed dodania notatki audytu (indeks od 0).

## Definicje energii i ekspozycji

Baza zdarzenia: średnia sygnału w domkniętym oknie [−5,−1] min (25 próbek).
Całkowanie prostokątne z wartościami lewostronnymi w **[0,15 min)**: 90 przedziałów
po 10 s. Wymagany punkt końcowy +15 min potwierdza pokrycie ostatniego przedziału.
Poprzedni kod sumował 91 próbek, odpowiadając 15 min 10 s.

- Energia dodatkowa: `sum(max(ΔP,0) × 10/3600)` kWh, przy założeniu, że moc jest w kW.
- Wskaźnik współwystępowania (`coincidence_energy`): ΔP > 5 kW i Δpył ≤ 5 mg/Nm³,
  bez warunku wcześniejszego piku. To odpowiada idei wcześniejszej maski,
  ale z poprawionym końcem przedziału.
- Energia ogonowa (`tail_energy`): ta sama maska mocy, lecz dopiero po **ostatnim**
  przekroczeniu Δpył > 5 w oknie i co najmniej 60 s zaobserwowanego powrotu poniżej
  progu. Jest to retrospektywna definicja diagnostyczna, nie reguła sterowania online.
  Próg wybiera próbki, a całkujemy całą ΔP, nie ΔP−5.
  Brak wzrostu pyłu lub brak pełnego powrotu daje zero energii obserwowanego ogona;
  osobne flagi `dust_excursion_observed` i `recovery_observed` rozróżniają te przypadki.
  Cenzurowane okno nie dowodzi zerowej energii poza horyzontem 15 min.
- Sekcje: wspólna maska ogona sumarycznego ESP, wkłady **ze znakiem** ΔP sekcji.
  Sumują się do całkowitej energii ogonowej. Wkład może być ujemny, a udział większy
  niż 1; nie jest to podział samych dodatnich kosztów. Przy zerowej sumie udział = NaN.
  Poprzednio maska sekcji pomijała próg mocy i niezależnie obcinała ujemne wkłady.
- Pokrycie: suma wyłącznie kolejnych przedziałów 10 s o skończonych wartościach
  na obu końcach. Luki i nieobserwowany przedział po ostatniej próbce nie są czasem
  pokrycia. Raportujemy oddzielnie rozpiętość kalendarzową i udział pokrycia.
- Sumy dotyczą **obserwowanych, zaakceptowanych zdarzeń**, nie automatycznie miesiąca.
  Domyślna ekstrapolacja roczna wyłączona (NaN). Opcjonalne `365/observed_days`
  jest tylko scenariuszem wymagającym reprezentatywności, korekty selekcji okien,
  brakujących zdarzeń, czasu pracy i rozkładu obciążeń. „Typical” jest filtrem po
  wyniku energetycznym i nie stanowi bezstronnej próby do ekstrapolacji.

## Status interpretacji

**Potwierdzone:** błędy implementacyjne powyżej i własności napraw w testach.
Przeliczenia na danych obserwacyjnych potwierdzają jedynie opisowe zależności
dla dostępnej próby, według jawnych definicji.

**Hipotezy:** reaktywna odpowiedź ECO na pył, nadmiernie długa odpowiedź mocy,
potencjalna oszczędność przez zmianę sterowania, przyczynowy wpływ rappingu.
Korelacja, kolejność median pików i energia ponad bazą nie rozstrzygają tych hipotez.
Nie nazywamy energii ogonowej ani oszczędnością, ani jej udowodnioną górną granicą:
podtrzymanie mocy może być przyczyną niskiego pyłu.

**Wiedza o instalacji potrzebna:** jednostki i punkt pomiaru mocy (sieć/zasilacz/
strona wtórna), opóźnienie transportu i filtracji pyłomierza, synchronizacja zegarów,
tryby ECO i nastawy/ograniczenia napięcia, znaczenie statusów strzepywaczy,
awarie i postoje, pozostałe strzepywacze i wspólny tor spalin. Zgodność U×I z tagiem
mocy jest kontrolą opisową, nie kalibracją ani dowodem fizycznego punktu pomiaru.

## Odtwarzanie i testy

Python nie był dostępny przez PATH i repo nie miało `.venv`. Utworzono lokalne
`.venv --system-site-packages` z Python 3.12.14 aplikacji. Pakiety uzupełniono w tym
środowisku; oryginalnego `requirements.txt` nie zmieniono. To środowisko audytu,
nie reprodukcja dawnych wersji. Dokładne wersje użyte w przeliczeniu zawiera lokalny
`results.json` oraz `docs/audit_environment.txt`.

Z katalogu repozytorium (PowerShell):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/run_methodology_audit.py
```

Skrypt wykonuje kod notebooków 01, 05, 06a, 06b i część zdarzeniową 04 (pierwotne
komórki 0–25 oraz 43), nie trenuje modeli 04 na niezaudytowanych cechach 02/03.
Nie zapisuje przemysłowych outputów do notebooków. Testy obejmują przeciek,
dodatni/ujemny lag, luki, duplikaty, brzegi okien, ekspozycję, powrót pyłu i zgodność
sum sekcji. Wyniki przeliczenia i ograniczenia wykonania: `audit_validation.md`.
