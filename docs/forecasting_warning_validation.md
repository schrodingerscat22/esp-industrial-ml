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
