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

## Lokalne przeliczenie kontrolne: D1

Przeliczenie z opóźnieniem pyłomierza 0 s (`availability_unverified`) objęło
fold D1: 64,54 obserwowanej godziny, 23 045 originów dla 1 min, 23 021 dla
3 min i 22 997 dla 5 min. Kontrola hashy wejść przeszła. MAE persistence /
XGBoost-PH wyniosło odpowiednio: 1 min `1,833 / 0,930`, 3 min `2,736 / 1,319`,
5 min `2,914 / 1,462` mg/Nm³. Są to wyłącznie lokalne, opisowe wyniki jednego
folda; nie są agregatem D1–D3 ani testem potwierdzającym.

## Lokalne przeliczenie kontrolne: D2

D2 z tym samym niepotwierdzonym opóźnieniem 0 s objęło 21 983 originy dla
1 min, 21 947 dla 3 min i 21 911 dla 5 min; kontrola hashy wejść przeszła.
MAE persistence / XGBoost-PH: 1 min `1,550 / 0,983`, 3 min `2,321 / 1,385`,
5 min `2,476 / 1,537` mg/Nm³. PH poprawił MAE względem persistence na każdym
horyzoncie D2, natomiast P bez historii pyłu nie był stabilnie lepszy od
persistence. To nadal wynik opisowy developmentu, bez łączenia foldów i bez
wniosku operacyjnego.

## Lokalne przeliczenie kontrolne: D3

D3 zakończył wszystkie horyzonty przy opóźnieniu 0 s. MAE persistence /
XGBoost-PH: 1 min `1,830 / 1,027`, 3 min `2,843 / 1,365`, 5 min
`3,041 / 1,541` mg/Nm³. P bez historii pyłu ponownie nie poprawił stabilnie
baseline’u; PH poprawił MAE dla każdego horyzontu. Wynik pozostaje opisowy.

## Lokalne przeliczenie: legacy evaluation

Ostatni fold objął trzy horyzonty. MAE persistence / XGBoost-PH wyniosło:
1 min `1,499 / 0,846`, 3 min `2,272 / 1,092`, 5 min `2,429 / 1,282`
mg/Nm³. PH było lepsze od persistence na każdym horyzoncie; P było blisko
persistence dla 1 min i słabsze dla 3/5 min. To ocena legacy na wcześniej
dostępnych danych, bez statusu potwierdzającego.
