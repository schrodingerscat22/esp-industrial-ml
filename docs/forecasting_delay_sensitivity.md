# Wrażliwość F1 na opóźnienie pyłomierza

Status: lokalna analiza developerska, 2026-09-11. Źródłem są oddzielne,
ignorowane artefakty lokalne; dokument zawiera tylko agregaty MAE w mg/Nm³.
Nie jest to potwierdzenie rzeczywistego opóźnienia instalacji.

## Protokół

Porównano XGBoost-PH z persistence w niezmienionych foldach D1–D3 dla
opóźnienia dostępności pyłu 0/30/60/120 s. Każdy wariant używa tego samego
seed, horyzontów direct 1/3/5 min i katalogu cech P/H. Persistence dostaje
ten sam opóźniony pomiar pyłu, więc porównanie pozostaje uczciwe.

## MAE XGBoost-PH

| Fold | Opóźnienie | 1 min | 3 min | 5 min |
|---|---:|---:|---:|---:|
| D1 | 0 s | 0,930 | 1,319 | 1,462 |
| D1 | 30 s | 1,022 | 1,304 | 1,482 |
| D1 | 60 s | 1,080 | 1,312 | 1,513 |
| D1 | 120 s | 1,142 | 1,330 | 1,576 |
| D2 | 0 s | 0,983 | 1,385 | 1,537 |
| D2 | 30 s | 1,140 | 1,418 | 1,543 |
| D2 | 60 s | 1,226 | 1,437 | 1,567 |
| D2 | 120 s | 1,355 | 1,440 | 1,578 |
| D3 | 0 s | 1,027 | 1,365 | 1,541 |
| D3 | 30 s | 1,140 | 1,397 | 1,553 |
| D3 | 60 s | 1,220 | 1,414 | 1,555 |
| D3 | 120 s | 1,305 | 1,418 | 1,577 |

## Wniosek developerski

PH pozostaje lepszy od persistence we wszystkich 36 porównaniach
fold × opóźnienie × horyzont. Wzrost opóźnienia zwykle zwiększa MAE, zwłaszcza
dla prognozy 1-minutowej, lecz przy 120 s przewaga nie znika. Nie wybieramy na
tej podstawie opóźnienia głównego: musi je potwierdzić rejestr dostępności
pyłomierza z instalacji. Wyniki nie są niezależnym testem potwierdzającym.

## Kolejny krok

Utworzyć i potwierdzić rejestr `tag, measurement_location,
archive_timestamp_meaning, online_available, availability_delay_s,
aggregation/filtering, unit, confirmed_by, confirmed_at`. Po otrzymaniu
potwierdzonego opóźnienia zamrażamy wariant główny; pozostałe zachowujemy jako
analizę wrażliwości. Następnie przygotowujemy F2 dla przekroczeń 20 i 40
mg/Nm³, bez doboru progu alarmowego na okresie legacy.
