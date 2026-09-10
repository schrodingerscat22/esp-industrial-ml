# Wyniki audytu modeli — 2026-09-10

Status: **zakończony etap porównania 02/03**. Protokół i zakres interpretacji:
`model_audit.md`. Wyniki są eksploracyjne; okres testowy był wcześniej analizowany.

## Wykonanie i integralność

- 14/14 testów przechodzi, w tym perturbacje przyszłych danych, wykluczenie
  bieżącego targetu, pojedyncza luka 20 s, dopasowanie schematu tylko na treningu.
- Notebook 02 wykonany w całości w trybie bez okna graficznego. Jego wynik clean
  jest identyczny z wejściem odtworzonym przez nowy skrypt eksperymentu.
- Pipeline wywoływany przez 03 zakończył dwa podziały walidacji i test;
  sześć dopasowań XGBoost oraz trzy oceny persistence. Nie uruchamiano ponownie
  całego treningu przez interfejs notebooka 03 — wywołuje ten sam skrypt.
- Siedem notebooków przechodzi walidację struktury i kompilację komórek.
  Outputy zmienionych notebooków są puste.
- Hashe wejść i wykonywanego kodu zgadzają się z końcowym manifestem.
  Zapisane metryki niezależnie odtworzono ze wszystkich predykcji przy użyciu
  scikit-learn; indeksy unikalne, uporządkowane, bez braków i po granicy treningu.
- Dane raw, istniejące v1/v2 i metadane wejściowe nie były nadpisywane.
  Wyniki jednostkowe, modele i macierze cech są tylko w ignorowanym audit_v3.

## Próba i podziały

Po usunięciu brakujących wartości: 210 642 wiersze, 75 sygnałów procesowych
i target. To o 2 wiersze mniej niż poprzednie clean z imputacją statusów.
Osiem luk zamiast sześciu, ciągłe pokrycie 24,37882 dnia przy 32 dniach rozpiętości.
W każdym podziale 1164 cechy procesowe i dodatkowo 19 cech historii pyłu.

| Podział | Początek oceny | Koniec oceny (włącznie) | Trening | Ocena |
|---|---|---|---:|---:|
| Walidacja 1 | 2025-07-12 15:05:20 | 2025-07-22 05:27:00 | 83 536 | 41 589 |
| Walidacja 2 | 2025-07-22 05:27:10 | 2025-07-27 02:58:30 | 125 125 | 41 768 |
| Test | 2025-07-27 02:58:40 | 2025-08-01 00:00:00 | 166 893 | 42 129 |

Znaczniki są interpretowane tak jak w istniejącym indeksie; strefa czasowa danych
wymaga potwierdzenia. Pełna historia usuwa 540 i 360 wierszy odpowiednio z pierwszej
i drugiej walidacji; na końcowym teście nie usuwa wierszy. Modele w obrębie każdego
podziału mają dokładnie te same znaczniki oceny.

## Wyniki

MAE/RMSE/bias w mg/Nm³. Bias = predykcja minus pomiar.

| Podział | Model | MAE | RMSE | Bias | R² |
|---|---|---:|---:|---:|---:|
| Walidacja 1 | Persistence (10 s) | 0,3424 | 1,4194 | 0,0004 | 0,9050 |
| Walidacja 1 | Procesowy | 2,1253 | 2,8694 | 0,2028 | 0,6118 |
| Walidacja 1 | Procesowy + historia pyłu | 0,3956 | 0,8724 | 0,0374 | 0,9641 |
| Walidacja 2 | Persistence (10 s) | 0,3851 | 1,5759 | 0,0000 | 0,9047 |
| Walidacja 2 | Procesowy | 2,7327 | 3,5566 | −2,3831 | 0,5148 |
| Walidacja 2 | Procesowy + historia pyłu | 0,4157 | 1,0512 | −0,0858 | 0,9576 |
| Test | Persistence (10 s) | 0,3124 | 1,2917 | −0,0001 | 0,9009 |
| Test | Procesowy | 1,4894 | 2,1955 | 0,3927 | 0,7137 |
| Test | Procesowy + historia pyłu | 0,3431 | 0,8249 | 0,0607 | 0,9596 |

Persistence wygrywa MAE we wszystkich trzech podziałach. Model z historią pyłu
wygrywa RMSE i R²; użyty trening minimalizuje błąd kwadratowy, więc kompromis
między MAE i RMSE nie jest sprzecznością. Wynik nie uzasadnia ogólnego twierdzenia,
że model jest lepszy od ostatniego pomiaru.

Na teście:

| Warstwa | n | MAE persistence | MAE procesowy | MAE procesowy + historia |
|---|---:|---:|---:|---:|
| 0–5 min po krytycznym rappingu | 2635 | 1,8311 | 2,9219 | 1,1799 |
| Poza tym oknem | 39 494 | 0,2110 | 1,3938 | 0,2872 |
| Pył >20 do 40 | 688 | 3,3605 | 6,0370 | 2,1484 |
| Pył >40 | 102 | 5,5980 | 9,7880 | 3,7091 |

Nieznany stan okna rappingu na tej wspólnej próbie testowej: 0 wierszy.
Wysokie stężenia są rzadkie, zależne czasowo i grupowane po rzeczywistym targetcie;
nie należy traktować 102 wierszy jako 102 niezależnych zdarzeń.

## Niepewność i wniosek roboczy

Bootstrap parowany całych dni, 1000 losowań, zakres percentyli 2,5–97,5%:

- MAE persistence: 0,2678–0,3588.
- MAE modelu procesowego: 1,3294–1,6780.
- MAE modelu z historią pyłu: 0,3256–0,3625.
- Różnica MAE „z historią minus persistence”: +0,0017 do +0,0589.

Tylko sześć dat kalendarzowych, w tym niepełne dni oraz końcowy punkt o północy.
Te zakresy są opisowe, a nie mocnym potwierdzeniem istotności statystycznej.

**Potwierdzona obserwacja:** historia pyłu pomaga względem modelu procesowego,
a model z historią ogranicza duże błędy i błędy przy rappingu kosztem MAE poza
rappingiem. Model procesowy ma niestabilność między okresami, szczególnie bias
w drugiej walidacji. **Hipoteza do dalszego badania:** modelowanie zdarzeń lub
dłuższego horyzontu może dać przewagę praktyczną; obecny eksperyment tego nie dowodzi.

Najbliższy krok: uzgodnić prognozowany horyzont i dostępność czujników, następnie
zamrozić protokół dla nowego okresu danych. Nie stroić modeli na obecnym teście.
