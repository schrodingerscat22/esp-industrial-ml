# Walidacja implementacji F2

F2 przewiduje, czy w kompletnym przyszłym oknie `(t, t+h]` pył przekroczy
analityczny próg 20 lub 40 mg/Nm³. Implementacja znajduje się w
`scripts/run_forecasting_warning_experiment.py`.

## Kontrakt etykiety

`event_h,c(t)` ma wartość 1, gdy maksimum wszystkich oczekiwanych próbek co
10 s w `(t, t+h]` jest większe od `c`. Jeżeli brakuje choć jednej próbki albo
okno przecina lukę telemetryczną, etykieta ma status `unknown` i nie trafia do
treningu ani oceny. Bieżąca wartość `y(t)` nie należy do przyszłego okna.

## Modele i ocena

W pierwszym wykonaniu porównujemy deterministyczny baseline persistence z
XGBoost-P i XGBoost-PH. Nie stosujemy oversamplingu. Dla obu modeli XGBoost
parametry są zamrożone przed wynikami: 200 drzew, depth 4, learning rate 0,05,
subsample i colsample 0,8, seed 42 oraz `tree_method=hist`.

Raport zawiera częstość zdarzeń, PR-AUC, Brier score i tabelę kalibracji w
dziesięciu stałych koszykach prawdopodobieństwa. Predykcje, modele i kalibracja
są lokalne w ignorowanym `data/processed/forecast_f2_v1/`.

Nie raportujemy jeszcze precision, recall, false alarms/hour ani lead time dla
konkretnego alarmu, ponieważ nie uzgodniono progu operacyjnego, dopuszczalnej
częstości fałszywych alarmów ani kosztu przeoczenia. Progi 20/40 pozostają
analityczne i nie są limitami prawnymi.

Parametry `--measurement-delay-seconds` i
`--process-availability-delay-seconds` rozdzielają dostępność pyłomierza od
dostępności tagów procesu. Oba odrzucają wartość, która wymagałaby przejścia
przez lukę telemetryczną. Krótki test integracyjny D1 (1 min, 20 mg/Nm³,
opóźnienie procesu 30 s) zakończył się poprawnie; nie jest on pełną analizą
wrażliwości ani wynikiem głównym.

Domyślny przebieg F2 obejmuje wyłącznie foldy D1--D3. Historyczny
`legacy_evaluation` wymaga jawnej opcji `--include-legacy` i nie należy do
agregatu developerskiego.

## Lokalne przeliczenie kontrolne: D1--D3

Wykonano 11 września 2026 na `dataset_clean.parquet`, tym samym zamrożonym
kodzie i trzech kalendarzowych foldach D1--D3 zdefiniowanych dla F1. Wyniki
poniżej są **developerską replikacją**, a nie niezależnym holdoutem ani
zatwierdzonym alarmem operacyjnym. Dane, predykcje, modele i tabele kalibracji
pozostają lokalne w ignorowanych katalogach `data/processed/forecast_f2_*`.

### Próg analityczny 20 mg/Nm³

Średnie, minimum i maksimum PR-AUC między foldami oraz średni Brier score:

| Horyzont | Model | PR-AUC: średnia (min--max) | Brier: średnia |
| --- | --- | ---: | ---: |
| 1 min | persistence | 0,460 (0,441--0,491) | 0,034 |
| 1 min | XGBoost-PH | 0,940 (0,925--0,952) | 0,012 |
| 3 min | persistence | 0,309 (0,278--0,337) | 0,089 |
| 3 min | XGBoost-PH | 0,927 (0,907--0,949) | 0,026 |
| 5 min | persistence | 0,293 (0,255--0,319) | 0,143 |
| 5 min | XGBoost-PH | 0,921 (0,910--0,942) | 0,041 |

Potwierdzone w tej replikacji: XGBoost-PH ma wyższy PR-AUC i niższy Brier
score od persistence w każdym z 3 foldów oraz we wszystkich 3 horyzontach.
To jest silny sygnał predykcyjny w aktualnym zbiorze, ale foldy pochodzą z
tego samego okresu danych, więc nie stanowi jeszcze potwierdzenia na nowym
okresie eksploatacji.

### Próg analityczny 40 mg/Nm³

PR-AUC XGBoost-PH w D1/D2/D3 wyniósł odpowiednio:

| Horyzont | D1 | D2 | D3 | Średnia |
| --- | ---: | ---: | ---: | ---: |
| 1 min | 0,844 | 0,923 | 0,855 | 0,874 |
| 3 min | 0,801 | 0,830 | 0,854 | 0,829 |
| 5 min | 0,805 | 0,787 | 0,855 | 0,815 |

### Co pozostaje nieustalone

- 20 i 40 mg/Nm³ są wyłącznie progami analitycznymi; nie wolno ich traktować
  jako nastaw alarmowych ani granic prawnych.
- Nie wybrano progu prawdopodobieństwa alarmu. Dlatego nie ma jeszcze
  uczciwej wartości precision, recall, false alarms/hour ani lead time.
- Semantyka i dostępność online tagów oraz rzeczywiste opóźnienie pyłomierza
  nadal wymagają potwierdzenia przez instalację. Wyniki F2 zakładają dostępność
  cech zgodną z aktualnym kontraktem opóźnień, a nie zweryfikowaną architekturą
  sterowania.
- Następny krok metodologiczny to zamrożenie konfiguracji, uzgodnienie kosztu
  alarmów i test na nowym, odseparowanym czasowo holdoucie.

## Analiza wrażliwości dostępności danych F2

Wykonano 12 września 2026 pełną analizę na foldach D1--D3 dla opóźnień
0/30/60/120 s, zawsze bez strojenia hiperparametrów. W każdym scenariuszu
opóźniano tylko jedno źródło: albo pyłomierz, albo tagi procesu; drugie
pozostawało przy 0 s. Wyniki są więc analizą jednoczynnikową, a nie symulacją
ich łącznego opóźnienia. Wszystkie artefakty pozostają lokalne i ignorowane
przez Git.

### XGBoost-PH, próg analityczny 20 mg/Nm³

Średni PR-AUC między D1--D3:

| Opóźnione źródło | Opóźnienie | 1 min | 3 min | 5 min |
| --- | ---: | ---: | ---: | ---: |
| brak | 0 s | 0,940 | 0,927 | 0,921 |
| tagi procesu | 30 s | 0,937 | 0,924 | 0,925 |
| tagi procesu | 60 s | 0,936 | 0,927 | 0,926 |
| tagi procesu | 120 s | 0,933 | 0,915 | 0,914 |
| pyłomierz | 30 s | 0,901 | 0,900 | 0,908 |
| pyłomierz | 60 s | 0,886 | 0,896 | 0,901 |
| pyłomierz | 120 s | 0,879 | 0,892 | 0,901 |

### Interpretacja potwierdzona w tej replikacji

- Wynik PH jest stosunkowo odporny na osobne opóźnienie tagów procesu do 120 s:
  największa zmiana średniego PR-AUC względem 0 s wynosi 0,012.
- Jest bardziej wrażliwy na opóźnienie pyłomierza, zwłaszcza przy horyzoncie
  1 min (spadek z 0,940 do 0,879 przy 120 s). Mimo tego PH nadal wyraźnie
  przewyższa persistence w każdym przeliczonym scenariuszu.
- Nie można z tego wyprowadzić rzeczywistego opóźnienia żadnego instrumentu ani
  jakości wariantu, w którym oba źródła są opóźnione równocześnie.

### Status po analizie

Zamknięto developerską analizę wrażliwości wymaganą przez metodologię dla
osobnych źródeł dostępności. Następny krok nie wymaga kolejnego strojenia:
zamrozić kod i konfigurację, a wyniki opisać jako retrospektywne do czasu
uzyskania potwierdzonych opóźnień lub nowego, odseparowanego holdoutu.

## Audyt F3: rola krytycznego strzepywania strefy 3

Audyt rozdziela istniejące predykcje F2 według tagu `008B05154` (strzepywanie
elektrod zbiorczych strefy 3). Wiersz jest oznaczony jako związany z rappingiem,
gdy origin przypada do 3 min po obserwowanym starcie albo gdy start wystąpi w
przyszłym horyzoncie. Jest to stratyfikacja **po fakcie**: przyszły start służy
wyłącznie do interpretacji wyniku i nie jest cechą modelu.

W 423 kompletnych profilach krytycznego rappingu mediana odstępu między startami
wynosi 82,83 min (10--90 percentyl: 82,67--84,50 min). W ciągu 3 min po starcie
93,6% profili przekracza 20 mg/Nm³, a 57,4% przekracza 40 mg/Nm³. To silnie
regularny mechanizm, który może być predykcyjnym skrótem, a nie dowodem ogólnej
zdolności do wykrywania niestabilności ESP.

### Wynik poza krytycznym rappingiem

Agregat D1--D3 XGBoost-PH:

| Próg | Horyzont | PR-AUC: całość | PR-AUC: po/z przyszłym rappingiem | PR-AUC: poza rappingiem | Dodatnie poza rappingiem |
| --- | ---: | ---: | ---: | ---: | ---: |
| 20 mg/Nm³ | 1 min | 0,940 | 0,977 | 0,887 | 3 042 |
| 20 mg/Nm³ | 3 min | 0,927 | 0,992 | 0,843 | 5 957 |
| 20 mg/Nm³ | 5 min | 0,921 | 0,990 | 0,819 | 8 569 |
| 40 mg/Nm³ | 1 min | 0,874 | 0,884 | 0,187 | 37 |
| 40 mg/Nm³ | 3 min | 0,829 | 0,844 | 0,075 | 64 |
| 40 mg/Nm³ | 5 min | 0,815 | 0,843 | 0,024 | 78 |

Wniosek potwierdzony: dla 20 mg/Nm³ model zachowuje istotny sygnał poza
krytycznym rappingiem, ale wynik ogólny jest częściowo wzmacniany przez ten
cykl. Dla 40 mg/Nm³ niemal wszystkie dodatnie przypadki są związane z tym
mechanizmem; liczba przypadków poza nim jest za mała do twierdzenia o ogólnym
ostrzeganiu przed wysokim pyłem.

Następny eksperyment F3 musi porównać pełny PH z PH bez wszystkich tagów
`esp_rapping` oraz z baseline'em wykorzystującym wyłącznie fazę cyklu strefy 3.
Osobno raportujemy prognozy przed obserwowanym startem rappingu. Dopiero to
rozstrzygnie, ile jakości wynika z harmonogramu, a ile z innych sygnałów procesu.

### Ablation F3 dla progu 20 mg/Nm³

Przeliczenie D1--D3 porównuje zamrożone modele: H (wyłącznie historia pyłu),
PH bez wszystkich tagów `esp_rapping`, model wyłącznie z krytycznym tagiem
strefy 3 i jego fazą oraz pełny PH. Średni PR-AUC:

| Horyzont | Stratum | H | PH bez rappingu | Tylko cykl strefy 3 | Pełny PH |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 min | całość | 0,856 | 0,880 | 0,502 | 0,940 |
| 1 min | poza rappingiem | 0,757 | 0,828 | 0,059 | 0,887 |
| 3 min | całość | 0,832 | 0,850 | 0,529 | 0,927 |
| 3 min | poza rappingiem | 0,687 | 0,770 | 0,094 | 0,843 |
| 5 min | całość | 0,842 | 0,857 | 0,580 | 0,921 |
| 5 min | poza rappingiem | 0,689 | 0,772 | 0,121 | 0,819 |

Potwierdzone: krytyczny cykl sam nie wyjaśnia wyniku PH i nie umie przewidywać
alarmów poza własnym oknem. Rapping wnosi dodatkową informację do pełnego PH,
jednak PH bez rappingu zachowuje większość jakości, a historia pyłu jest silnym
baseline'em. Wynik pełnego PH należy więc opisywać jako połączenie dynamiki
pyłu, stanu procesu i przewidywalnych zaburzeń po rappingu — nie jako czyste
wykrywanie niezależnych awarii procesu.
