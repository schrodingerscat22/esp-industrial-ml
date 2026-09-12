# Aktualny plan doktoratu ESP

Stan: 2026-09-12. Kontynuować z gałęzi `codex/methodology-audit`.
Użytkownik zezwolił na commit i push kodu, testów i dokumentacji na tę gałąź.
Zachować niezacommitowane zmiany. Dane źródłowe są tylko do odczytu; dane
przemysłowe, modele, predykcje i szczegółowe outputy pozostają poza Git.

## Bieżąca decyzja: wracamy do pytania energetycznego

Głównym zamiarem doktoratu jest poprawa energetyczna; temat pozostaje otwarty,
a promotor dopuszcza zmianę kierunku. Użytkownik wskazał brak praktycznego
działania po prognozie cyklicznego piku za ostatnią strefą. Dalsza poprawa F2
nie jest obecnie priorytetem. Dotychczasowe wyniki zachowujemy jako materiał
metodologiczny, bez twierdzenia o skuteczności operacyjnych alarmów.

Nowy plan: [electrical_energy_methodology.md](electrical_energy_methodology.md).
Łączymy U–I z wilgotnością, temperaturą, przepływem, obciążeniem i cyklami
wszystkich strzepywaczy. U/I jest pozorną rezystancją, nie pomiarem rezystywności
pyłu. Prawie algebraiczna zależność P od U*I i zamknięta pętla regulatora
uniemożliwiają uznanie prostego modelu predykcyjnego za optymalizator energii.

**E1 zakończono decyzją B:** sygnały U–I i cykle są poprawne do opisu stanu,
ale nie ma wystarczająco porównywalnych bloków do benchmarku energetycznego.
Wynik: [electrical_energy_validation.md](electrical_energy_validation.md).
E1.5 potwierdził, że archiwum nie zawiera opisanej nastawy, limitu, ECO ani
komendy regulatora: [control_signal_audit.md](control_signal_audit.md).
E2 może być wyłącznie małym testem diagnostycznego przyrostu informacji, bez
optymalizacji nastaw. Lokalny wynik rozpoznania:
`data/processed/energy_idea_review_20260912/preflight.json`.

E1 kończy się decyzją: A — sygnał procesu i pokrycie energetyczne, B — sam
potencjał monitorowania stanu, C — brak uzasadnienia dalszych modeli na tym
zbiorze. E2 jest warunkowym, małym testem przyrostu informacji procesowej.
Oszczędności wskutek zmiany nastaw wymagają osobnej walidacji przyczynowej.
Brak dodatkowych informacji z instalacji nie blokuje opisowego E1.

## Wykonane etapy i dokumenty źródłowe

| Etap | Status i dokument |
| --- | --- |
| Audyt 01, lagów, luk, rappingu i energii | Naprawiony i przeliczony; [methodology_audit.md](methodology_audit.md), [audit_validation.md](audit_validation.md) |
| Audyt modeli 02/03 | Przeliczony; [model_audit.md](model_audit.md), [model_validation.md](model_validation.md) |
| F1, horyzonty 1/3/5 min | Wdrożone, D1–D3 i analiza opóźnień; [forecasting_validation.md](forecasting_validation.md), [forecasting_delay_sensitivity.md](forecasting_delay_sensitivity.md) |
| F2 i wrażliwość dostępności | Wdrożone i przeliczone; [forecasting_warning_validation.md](forecasting_warning_validation.md) |
| F3: wpływ cyklu i ablation | Przeliczone D1–D3; końcowe sekcje raportu F2 |
| Kierunek E | E1: decyzja B; E1.5: brak zmiennej sterowania, [raport](control_signal_audit.md) |

Cały dotychczas oglądany miesiąc pozostaje okresem rozwojowym; nie odzyskujemy
niezależnego holdoutu przez ponowny podział tych samych danych. Nowe obliczenia
nie zmieniają definicji F1–F3 w [forecasting_methodology.md](forecasting_methodology.md).
Kod czasu: `src/time_analysis.py`. Źródła obliczeń audit_v2 i audit_v3 oraz
wszystkie lokalne katalogi forecast pozostają ignorowane przez Git.

Poniższe wymagania przekrojowe pozostają ważne. Nie są zleceniem ponownego
wykonania zakończonych treningów ani warunkiem wstrzymania E1.

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
