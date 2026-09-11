# Metodologia prognozowania pyłu 1/3/5 min — projekt do wdrożenia

Wersja: 0.3, 2026-09-11. Status: F1 i implementacja F2 wdrożone; lokalne
przeliczenia są zapisywane poza Git. F2 nie ma jeszcze progu operacyjnego.
Kontynuacja audytów `methodology_audit.md`, `model_audit.md` i
`model_validation.md`. Implementację należy wykonać na gałęzi
`codex/methodology-audit`, używając Terra medium. Dane przemysłowe, predykcje,
modele i macierze cech pozostają poza Git; do Git trafiają kod, testy,
agregaty metodologiczne i dokumentacja.

## 1. Pytanie badawcze

W chwili `t` przewidujemy stężenie pyłu za ESP:

- `y(t + 1 min)` — 6 próbek,
- `y(t + 3 min)` — 18 próbek,
- `y(t + 5 min)` — 30 próbek.

Każdy horyzont jest osobnym zadaniem direct forecasting. Model 5-minutowy
przewiduje bezpośrednio `y(t+5 min)`; nie składa trzydziestu kolejnych prognoz.
Ogranicza to propagację błędów i pozwala oceniać każdy horyzont niezależnie.

Protokół rozdziela dwa zastosowania, ponieważ mają inne funkcje straty:

1. **F1 — prognoza ciągła:** jak dokładnie przewidujemy wartość stężenia?
2. **F2 — wczesne ostrzeganie:** czy w przedziale `(t,t+h]` wystąpi
   przekroczenie ustalonego progu?

Nie wybieramy modelu F1 na podstawie zachowania na kilku pikach i nie nazywamy
dobrego MAE dowodem dobrego ostrzegania. Wyniki obu zastosowań są raportowane
osobno. Analiza nie jest jeszcze modelem kontrfaktycznym i nie uzasadnia zmiany ECO.

## 2. Kontrakt informacji dostępnej w chwili prognozy

### 2.1. Warianty wejścia

Porównujemy trzy rozłączne pytania naukowe:

| Wariant | Dane dostępne do `t` | Interpretacja |
|---|---|---|
| H — historia pyłu | pomiary pyłu do `y(t)` | czysta dynamika/autoregresja |
| P — proces | sygnały procesowe i elektryczne do `x(t)`, bez pyłu | prognoza/soft sensor bez pyłomierza |
| PH — proces + historia | H oraz P | przyrost informacji procesowej ponad historię pyłu |

W poprzednim nowcastingu historia zaczynała się od `y(t−10 s)`, ponieważ celem
było `y(t)`. W prognozie przyszłości `y(t)` jest legalnym wejściem, jeżeli pomiar
jest rzeczywiście dostępny w chwili wydania prognozy. Jeśli instalacja dostarcza
pył z opóźnieniem `d`, ostatnim wejściem jest `y(t−d)`. Implementacja musi mieć
parametr `measurement_delay_seconds`, bez ręcznego przesuwania kolumn.

### 2.2. Rejestr dostępności tagów

Przed interpretacją wyniku trzeba utworzyć wersjonowaną tabelę:

`tag, measurement_location, archive_timestamp_meaning, online_available,
availability_delay_s, aggregation/filtering, unit, confirmed_by, confirmed_at`.

Podstawowy eksperyment developerski może tymczasowo przyjąć opóźnienie 0 s,
ale musi być oznaczony jako `availability_unverified`. Obowiązkowa analiza
wrażliwości: opóźnienie pyłomierza i bieżących sygnałów `0/30/60/120 s`.
Nie wolno wybrać najkorzystniejszego opóźnienia jako wyniku głównego. Wynik główny
używa opóźnienia potwierdzonego przez instalację; pozostałe są analizą wrażliwości.

Nie używamy przyszłych wartości procesu. Planowany przyszły rapping albo nastawa
mogą wejść do osobnego wariantu wyłącznie po potwierdzeniu, że harmonogram byłby
znany w `t`; nie mieszamy go z podstawowym wynikiem.

## 3. Dane i zasady czasu

Źródło developerskie: istniejący `dataset_clean.parquet` i semantyczna lista
wejść z `tag_classification_v1.xlsx`. Są to dane wcześniej analizowane, więc
cały etap na obecnym okresie jest **development/legacy evaluation**, nie
niezależnym testem publikacyjnym.

Reguły obowiązkowe:

- indeks `DatetimeIndex`, rosnący, bez duplikatów i bez brakujących timestampów;
- oczekiwany krok 10 s; każdy inny odstęp rozpoczyna nowy segment historii;
- żadna cecha nie przechodzi przez granicę segmentu;
- brak `bfill`; target nigdy nie jest imputowany;
- usunięcie albo imputacja wejścia musi być dopasowana tylko na treningu,
  ograniczona czasowo i raportowana. W wersji podstawowej stosujemy complete case;
- etykieta punktowa istnieje tylko, gdy jest próbka dokładnie w `t+h`;
- dla etykiety `max(y(t+10 s),...,y(t+h)) > threshold` wymagamy wszystkich
  przyszłych próbek w oknie. Niepełne okno ma status unknown, a nie klasę 0;
- dla prognozy punktowej nie wymagamy kompletności próbek *pośrednich* po wydaniu
  prognozy, jeżeli `y(t+h)` istnieje. Dla metryk ścieżki i przekroczenia wymagamy
  pełnego przyszłego okna;
- wszystkie powody odrzucenia originów są liczone osobno: brak historii,
  brak wejścia, brak etykiety, niepełna przyszła ścieżka, nieznana dostępność.

Wynik ma raportować rozpiętość kalendarzową, obserwowany czas, liczbę segmentów,
czas luk, liczbę originów i liczbę niezależnych epizodów. Duża liczba próbek 10 s
nie jest utożsamiana z dużą liczbą niezależnych obserwacji.

## 4. Etykiety

### 4.1. Prognoza ciągła F1

`target_h(t) = y(t+h)` dla `h ∈ {1,3,5 min}`. Trenujemy osobny model na każdy
horyzont. Stężenia raportujemy w oryginalnej skali mg/Nm³. Predykcje ujemne są
obcinane do zera; liczba i wielkość obcięć są raportowane.

### 4.2. Wczesne ostrzeganie F2

`event_h,c(t) = 1`, jeśli maksimum kompletnej ścieżki `(t,t+h]` przekracza `c`.
Do czasu uzgodnienia granicy operacyjnej raportujemy progi analityczne 20 i
40 mg/Nm³. Nie nazywamy ich limitami prawnymi ani alarmami instalacji.

Próbki przekroczeń łączymy w epizody. Nowy epizod zaczyna się przy przejściu
z wartości `≤c` do `>c` w ciągłym segmencie. Sąsiednie alarmy modelu łączymy
w jedno ostrzeżenie do końca horyzontu/cooldown. Wynik epizodowy liczy:

- trafiony epizod, jeżeli co najmniej jeden alarm wystąpił 0–h przed startem;
- czas wyprzedzenia pierwszego poprawnego alarmu;
- fałszywy alarm, jeżeli w jego przyszłym pełnym oknie nie ma przekroczenia;
- liczbę fałszywych alarmów na obserwowaną godzinę, nie na rozpiętość kalendarza.

## 5. Cechy

Schemat cech powstaje wyłącznie z treningu danego folda. Kod powinien rozszerzyć
`src/model_features.py`, zachowując dotychczasowe zabezpieczenia czasu.

### H — historia pyłu

- bieżący dostępny pomiar z uwzględnieniem `measurement_delay_seconds`;
- lagi 10/30/60/120/300/600/1800 s;
- średnia, mediana, minimum, maksimum, odchylenie i rozstęp międzykwartylowy
  z 1/5/10/30 min;
- różnice i nachylenie z 1/3/5 min;
- czas od ostatniego przekroczenia progów analitycznych, liczony po timestampach.

### P — proces

- bieżące wartości dostępnych tagów;
- te same lagi 10–1800 s;
- mean/std/min/max oraz różnice dla sygnałów analogowych;
- stany i obserwowane starty wszystkich strzepywaczy;
- czas od ostatniego startu każdego strzepywacza, bez przejścia przez luki;
- sumy mocy/napięcia wyłącznie gdy jednostki i definicje tagów są potwierdzone;
- opcjonalna godzina/dzień jako analiza wrażliwości, nie domyślny nośnik
  „zapamiętania” badanego miesiąca.

Nie tworzymy 1164 cech bez kontroli. Raport zawiera liczbę cech w rodzinach,
udział braków i stałość schematu między foldami. Cechy redundantne mogą zostać
ograniczone po walidacji, bez zaglądania do przyszłego testu.

### 5.1. Zamrożony katalog P dla F1 v1

W pierwszym wykonaniu P używa wszystkich bieżących tagów, lagów 1/5/30 min,
mean i std z okien 5/30 min oraz różnic 3/5 min dla tagów ciągłych. Stany,
obserwowane starty i czas od startu wszystkich strzepywaczy pozostają w zbiorze.
To świadomie ograniczony katalog, ustalony przed porównaniem wyników F1: chroni
przed niekontrolowanym rozwinięciem cech dla 75 tagów i umożliwia odtwarzalne
wykonanie na stanowisku developerskim. Pełny katalog H pozostaje zgodny z
listą powyżej. Rozszerzenie P wymaga nowej wersji protokołu i walidacji bez
użycia przyszłego holdoutu.

## 6. Modele i baseline’y

Każdy model jest direct i oddzielny dla 1/3/5 min.

### Obowiązkowe baseline’y

1. **Persistence:** `ŷ(t+h)=y(t)` albo ostatni dostępny pomiar po uwzględnieniu
   opóźnienia czujnika. Jest głównym odniesieniem.
2. **Median level:** mediana targetu z treningu; kontrola elementarna.
3. **Linear AR:** regularized linear regression na H; interpretable baseline.

### Modele kandydackie

- XGBoost-H — tylko historia pyłu;
- XGBoost-P — tylko proces;
- XGBoost-PH — proces i historia;
- klasyfikatory XGBoost-P i XGBoost-PH dla F2, bez oversamplingu przez granice czasu.

Pierwsze wykonanie używa jednej konfiguracji zamrożonej przed wynikami:
200 drzew, depth 4, learning rate 0,05, subsample i colsample 0,8, seed 42,
`tree_method=hist`. To punkt startowy z audytu nowcastingu, a nie wynik strojenia
na nowym zadaniu. Optymalizujemy wersję podstawową dla MAE; wariant squared-error
raportujemy jako analizę kompromisu MAE/RMSE, jeżeli biblioteka wspiera stabilnie
obie funkcje celu.

Sieci LSTM/transformer nie wchodzą do pierwszego wdrożenia. Obecne 24,38 dnia
ciągłych obserwacji daje wiele skorelowanych próbek, ale niewiele niezależnych dni
i reżimów. Model sekwencyjny można dodać dopiero, gdy proste modele i nowy holdout
ustanowią wiarygodny punkt odniesienia.

## 7. Rolling-origin validation i purge

Rolling-origin z rozszerzanym treningiem pozwala sprawdzić zmianę jakości w czasie
i jest zalecanym sposobem oceny prognoz poza próbą. Projekt wyboru foldów musi być
jawny, ponieważ liczba originów i różnorodność okresów wpływają na wiarygodność
oceny [Tashman, 2000](https://doi.org/10.1016/S0169-2070(00)00065-0).

### Development na obecnych danych

Granice kalendarzowe, niezależne od liczby zachowanych wierszy:

| Fold | Trening | Ocena |
|---|---|---|
| D1 | 2025-06-30 do 2025-07-12 00:00 | 2025-07-12 do 2025-07-17 00:00 |
| D2 | do 2025-07-17 00:00 | 2025-07-17 do 2025-07-22 00:00 |
| D3 | do 2025-07-22 00:00 | 2025-07-22 do 2025-07-27 00:00 |
| Legacy evaluation | do 2025-07-27 00:00 | 2025-07-27 do końca danych |

Foldów nie przesuwamy po obejrzeniu wyników. Luki są częścią realnej ekspozycji;
każdy fold raportuje obserwowane godziny i zdarzenia. Jeżeli fold ma mniej niż
24 h obserwacji lub 10 epizodów dla ocenianego progu, jego metryki epizodowe są
oznaczane jako niestabilne i używane wyłącznie w agregacie.

### Purge i dostępna historia

Dla początku oceny `T` trening zawiera tylko originy spełniające `t+h<T`.
Zapobiega to wejściu treningowej etykiety do okresu oceny. Dla horyzontów
1/3/5 min purge wynosi odpowiednio 1/3/5 min.

Ocena może użyć historii sprzed `T`, bo w rzeczywistym wdrożeniu byłaby znana.
Nie wymagamy 30-minutowej pustej przerwy tylko dlatego, że najdłuższa cecha ma
30 min; wymagamy pełnej, wcześniejszej historii cechy. Każdy scaler, selektor,
imputer, kalibrator i próg alarmu jest dopasowany wyłącznie na treningu.

### Nowy test potwierdzający

Przed wczytaniem nowych danych zamrażamy commit, hashe kodu, konfigurację,
progi i kryteria sukcesu. Minimum do wstępnego testu: 14 dni kalendarzowych,
co najmniej 10 pełnych dni obserwacji i 100 startów krytycznego rappingu.
Do wniosku publikacyjnego preferowany jest co najmniej pełny miesiąc pracy oraz
więcej niż jeden sezon/reżim obciążenia. Jeśli minimum nie jest spełnione,
raportujemy wynik opisowy i zbieramy dane dalej.

Nowego holdoutu używamy raz. Po jego otwarciu każda zmiana modelu tworzy nową
wersję badania i wymaga kolejnego okresu potwierdzającego.

## 8. Metryki

### F1 — ciągłe

Główna metryka: MAE osobno dla każdego horyzontu. Dodatkowe:

- RMSE, bias, median absolute error i R² jako opis;
- MAE skill: `1 − MAE_model / MAE_persistence`;
- MASE z mianownikiem wyliczonym wyłącznie na treningu. MASE pozwala skalować
  błąd względem naiwnej prognozy [Hyndman i Koehler, 2006](https://doi.org/10.1016/j.ijforecast.2006.03.001).
  Dla każdego horyzontu mianownik to średni treningowy błąd
  `|y(t)−y(t−h)|`, liczony wyłącznie wewnątrz ciągłych segmentów;
- 90. i 95. percentyl błędu bezwzględnego;
- metryki dla rappingu 0–5 min, poza rappingiem, przedziałów pyłu, dni,
  kwartyli obciążenia i ciągłych segmentów;
- osobno wszystkie originy co 10 s i próbka co 60 s, aby pokazać wpływ
  nakładających się prognoz.

### F2 — ostrzeganie

Average precision/PR-AUC, Brier score i wykres kalibracji. PR-AUC jest szczególnie
istotne przy rzadkich przekroczeniach; sama ROC-AUC może wyglądać dobrze przy
silnej nierównowadze klas [Davis i Goadrich, 2006](https://minds.wisconsin.edu/handle/1793/60482).
Po wyborze progu wyłącznie na walidacji: precision, recall, false alarms/hour,
event recall i rozkład lead time. Zawsze podajemy częstość klasy dodatniej.

Progi alarmu nie są dobierane na teście. Do ich zatwierdzenia potrzebny jest
koszt przeoczenia i dopuszczalna liczba fałszywych alarmów od użytkownika instalacji.

## 9. Niepewność i porównanie modeli

Podstawą jest różnica straty liczona parami na tych samych originach.
Raportujemy rozkład jakości między foldami oraz bootstrap całych dni. Przy mniej
niż 20 obserwowanych dniach przedziały mają status opisowy; przy nowym teście
docelowo co najmniej 30 dni. Nakładające się błędy wielohoryzontowe są zależne,
więc nie stosujemy testu zakładającego niezależne próbki 10 s.

Jako kontrolę można raportować test Diebolda–Mariano z estymacją wariancji
odporną na autokorelację i lagiem co najmniej `h−1`; test ten został zaprojektowany
dla porównywania prognoz przy skorelowanych błędach
[Diebold i Mariano, 1995](https://doi.org/10.1080/07350015.1995.10524599).
Nie zastępuje on wielodniowej replikacji ani praktycznej wielkości efektu.

Dla trzech horyzontów każda deklaracja „lepszy” musi uwzględnić wielokrotne
porównania, np. korektą Holma. Można też sformułować z góry jeden główny horyzont;
do czasu decyzji wszystkie trzy są równorzędne i raportujemy pełny zestaw wyników.

## 10. Kryteria decyzji

### Bramka techniczna

- testy perturbacji przyszłego targetu i procesu;
- test dokładnego wyrównania 6/18/30 próbek i timestampów;
- test purge przy każdej granicy;
- test braku cech przekraczających lukę;
- test niepełnego okna F2 jako unknown;
- identyczne originy dla porównywanych modeli;
- odtworzenie metryk z zapisanych predykcji;
- hashe wejść/kodu i potwierdzenie braku zmian danych źródłowych.

### Bramka developerska

Model przechodzi do zamrożonego testu tylko, gdy:

- ma dodatni pooled MAE skill względem persistence;
- poprawa ma ten sam znak w co najmniej dwóch z trzech foldów D1–D3;
- nie wykazuje nieakceptowalnego bias w żadnym reżimie;
- dla F2 przewyższa częstość bazową PR-AUC i spełnia jeszcze nieuzgodniony
  budżet fałszywych alarmów;
- kod i konfiguracja są zamrożone przed nowym holdoutem.

Warunki oceniamy oddzielnie dla każdego horyzontu i zastosowania. Nie przenosimy
zaliczenia horyzontu 1 min na 3 lub 5 min.

„Nieakceptowalny bias”, minimalna praktyczna poprawa MAE oraz budżet alarmów
muszą zostać wpisane liczbowo po konsultacji z instalacją, przed testem
potwierdzającym. Bez tych wartości nie ogłaszamy sukcesu operacyjnego.

### Bramka potwierdzająca

Na nowym holdoucie wymagamy dodatniego efektu względem persistence oraz
przedziału ufności dla sparowanej różnicy MAE zgodnego z wcześniej wpisaną
minimalną poprawą. Model F2 musi utrzymać uzgodniony recall i false alarms/hour.
Wyniki dla wysokiego pyłu raportujemy także epizodami; liczba próbek nie zastępuje
liczby zdarzeń.

Model P może być wartościowym soft sensorem nawet wtedy, gdy przegrywa z PH,
ale porównujemy go z baseline’em właściwym dla działania bez pyłomierza.
Przewaga PH nad H odpowiada na pytanie, czy proces dodaje informację ponad
autokorelację pyłu.

## 11. Handoff do implementacji na Terra medium

Implementacja powinna powstać jako jeden etap z następującymi artefaktami:

1. `src/forecast_features.py` — dostępność, opóźnienia, cechy H/P/PH i etykiety.
2. `src/forecast_validation.py` — kalendarzowe foldy, purge, metryki i epizody.
3. `scripts/run_forecasting_experiment.py` — konfiguracja → pełny manifest lokalny.
4. `tests/test_forecast_features.py` i `tests/test_forecast_validation.py`.
5. `notebooks/07_multihorizon_dust_forecasting.ipynb` — cienki interfejs,
   bez logiki biznesowej i bez zapisanych danych przemysłowych w outputach.
6. Lokalne `data/processed/forecast_v1/`: design.json zapisany przed fit,
   report.json, agregaty, predykcje, modele, feature schema i log wykonania.
7. `docs/forecasting_validation.md` — wyniki potwierdzone, hipotezy i ograniczenia.

Najpierw wdrożyć F1 z persistence/H/P/PH i trzema horyzontami. Następnie F2,
używając tych samych foldów. Nie stroić hiperparametrów w pierwszym wykonaniu.
Nie uruchamiać optymalizacji ECO ani ekstrapolacji oszczędności w tym etapie.

## 12. Informacje wymagane od instalacji

Nie blokują one technicznego wdrożenia wersji developerskiej, ale blokują wynik
operacyjny i publikacyjny:

1. Rzeczywiste opóźnienie oraz filtracja pyłomierza i znaczenie jego timestampu.
2. Które tagi są online dostępne w momencie prognozy i z jakim opóźnieniem.
3. Próg ostrzegania oraz czy liczy się wartość chwilowa, średnia czy inna agregacja.
4. Dopuszczalne false alarms/hour i minimalny wymagany recall/lead time.
5. Okresy postoju, awarii, kalibracji, rozruchu i ręcznego/automatycznego ECO.
6. Czy przyszły harmonogram rappingu jest znany sterownikowi przed zdarzeniem.
