# Walidacja implementacji F1

Wersja implementacji: F1 v1, 2026-09-10. Ten dokument opisuje kod i zasady
interpretacji lokalnych artefaktów. Nie zawiera danych przemysłowych,
predykcji ani modeli.

## Zakres

`scripts/run_forecasting_experiment.py` wykonuje oddzielne prognozy bezpośrednie
`y(t+60 s)`, `y(t+180 s)` i `y(t+300 s)` w ustalonych foldach D1–D3 oraz
`legacy_evaluation`. Warianty H, P i PH są oceniane na tych samych originach
w obrębie folda i horyzontu, razem z persistence, medianą treningową i
regularizowanym modelem liniowym H.

Artefakty lokalne trafiają do `data/processed/forecast_v1/`, które Git ignoruje:
`design.json`, `report.json`, agregaty metryk, predykcje i modele. Przed
dopasowaniem zapisywane są hashe wejść i kodu; po dopasowaniu sprawdzany jest
hash obu wejść. Parametr opóźnienia pyłomierza jest jawny; wartość domyślna
0 s ma status `availability_unverified`.

## Zabezpieczenia czasu

- target istnieje wyłącznie przy dokładnym timestampie `t+h`;
- cechy historii, lagi, okna, starty rappingu i MASE nie przechodzą przez lukę;
- target punktowy może przejść przez przyszłą lukę tylko wtedy, gdy dokładny
  endpoint istnieje;
- trening spełnia `t+h < początek_oceny`; w foldzie ograniczonym origin oceny
  spełnia `t < koniec_oceny-h`;
- medianowy imputer modelu liniowego jest dopasowywany tylko na treningu.

Brak czasu od zdarzenia przed pierwszym zaobserwowanym przekroczeniem lub
rappingiem jest brakiem strukturalnym. XGBoost obsługuje go natywnie; model
liniowy imputuje go medianą treningową. Nie jest to interpolacja przez lukę.

## Weryfikacja automatyczna

`python -m unittest discover -s tests -v` obejmuje 23 testy, w tym testy F1
dla dokładnego targetu, opóźnienia pomiaru, braku wpływu przyszłości na cechy,
luk historii, purge, MASE i nieznanego okna rappingu po luce.

## Interpretacja wyników

Wynik obecnych danych jest tylko development/legacy evaluation. `MAE` jest
metryką główną; raport zawiera także RMSE, bias, medianę oraz percentyle błędu,
R², MASE, skill względem persistence, obcięcia predykcji, stratyfikacje i
opisowy bootstrap dni dla okresu legacy. Brak potwierdzonej dostępności tagów,
brak nowego holdoutu i mała liczba niezależnych dni wykluczają twierdzenia
operacyjne lub publikacyjne.
