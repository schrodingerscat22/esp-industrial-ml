# Aktualny plan doktoratu ESP

Stan: 2026-09-10. Kontynuować z gałęzi `codex/methodology-audit`.
Najpierw przeczytać `methodology_audit.md` i `audit_validation.md`.
Kod wspólny: `src/time_analysis.py`; lokalny manifest i wyniki:
`data/processed/audit_v2/results.json`. Nie publikować danych ani outputów
przemysłowych; nie nadpisywać raw lub istniejących v1. Brak zgody na push.

## 1. Zamknięcie kontraktu danych i celu predykcji

- Uzgodnić online nowcasting, prognozę o konkretnym horyzoncie i/lub soft sensor
  bez pyłomierza. Jawnie ustalić dostępność każdego sygnału w chwili predykcji.
- Odtworzyć lineage ZIP → interim → clean. Sprawdzić strefę czasową, DST,
  duplikaty, resampling, interpolację, usunięte wiersze i przyczyny luk.
- Uzgodnić z technologiem tagi mocy, statusy i tryby ECO, opóźnienie pyłomierza,
  filtrację, synchronizację oraz granice bezpiecznej pracy.

Kryterium zakończenia: wersjonowany kontrakt sygnałów i czasu, rejestr braków,
jednoznaczna definicja targetu i horyzontu. Bez tego nie zatwierdzać efektów fizycznych.

## 2. Pełny audyt modeli 02/03 i powtarzalna walidacja

- Przenieść feature engineering do testowalnych funkcji. Sprawdzić target,
  diff/rolling/lag, luki i dostępność czasową; wygenerować nową wersję artefaktów.
- Ustalić jeden końcowy test chronologiczny przed wyborem cech i hiperparametrów.
  W treningu stosować walidację kroczącą; dopasowanie transformacji tylko na train.
  Długość odstępu między zbiorami wynika z horyzontu etykiety i okien, a nie arbitralnej liczby.
- Porównać persistence, model procesowy bez historii pyłu i model z historią pyłu
  na dokładnie tych samych znacznikach testowych. Nie utożsamiać lepszego wyniku
  na próbie po usunięciu pików z lepszym modelem dla pełnej emisji.
- Raportować MAE/RMSE/bias, zakresy stężeń, zdarzenia, obciążenie i stabilność
  między okresami; niepewność przez bootstrap bloków/dni zamiast niezależnych próbek.

Kryterium zakończenia: odtwarzalny eksperyment i metryki bez przecieku, zgodne
z rzeczywistym zastosowaniem. Dawne metryki katalogu danych pozostają historyczne.

## 3. Rapping i ECO: opis, odporność, identyfikacja

- Raportować liczbę wszystkich startów, pełnych okien, odrzuceń i cenzurowań.
  Sprawdzić nakładanie **wszystkich** strzepywaczy, nie tylko krytycznego tagu.
- Porównać bazę [−5,−1] z alternatywami, okna 10/15/20 min, progi pyłu i mocy,
  czas potwierdzenia powrotu, reguły izolacji zdarzeń i wpływ filtracji pomiarów.
- Raportować osobno energię współwystępowania i rzeczywistego ogona czasowego,
  pełną próbę i filtry po wyniku. Uwzględnić cenzurowanie i selekcję okresów bez luk.
- Analizować opóźnienia w segmentach i reżimach; wspólne trendy i autokorelacja
  wymagają kontroli. Maksimum korelacji nie identyfikuje regulatora ani przyczyny.
- Dopiero po uzgodnieniu instalacji: porównywalne okresy kontrolne, warunkowanie
  na obciążeniu, paliwie, przepływie i trybie ECO; ocena dostępnego nakładania
  warunków pracy (06b) przed próbą wnioskowania o zmianie nastaw.

Kryterium zakończenia: stabilne obserwacje z niepewnością oraz jawne oddzielenie
wniosków opisowych od przyczynowych.

## 4. Oszczędności i ewentualny eksperyment sterowania

Ekstrapolację odblokować dopiero po zdefiniowaniu reprezentatywnej ekspozycji,
liczby godzin pracy rocznie i poprawnej częstości zdarzeń. Koszty liczyć na
uzgodnionej jednostce energii i taryfie. Redukcja energii ogonowej to hipoteza:
wymaga zweryfikowanego kontrfaktycznego modelu lub zatwierdzonego eksperymentu
na instalacji, z ograniczeniami emisji i procedurą wycofania. Ten etap audytu
nie zmienia nastaw ani nie rekomenduje ich wdrożenia.
