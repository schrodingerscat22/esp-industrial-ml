# Audyt reakcji elektrycznej ESP po zmianie wskazania pyłu

Stan: 2026-09-13. Plan zamrożony przed uruchomieniem nowych obliczeń. Celem jest
sprawdzenie, czy dane są zgodne z opóźnioną odpowiedzią elektryczną po zmianie
wskazania pyłu. Nie identyfikujemy wejścia regulatora, efektu przyczynowego ani
oszczędności energii.

## Dane i czas

Wejście to `data/processed/audit_v3/df_model_clean_v1.parquet`. Wszystkie
opóźnienia, różnice, przyszłe cele i epizody są liczone wyłącznie w ciągłych
segmentach obserwacji co 10 s. Wymagane są dokładne znaczniki obu końców różnicy
lub horyzontu; luka daje brak wyniku, nigdy imputację.

Sygnały wyniku: suma mocy trzech zespołów, średnie napięcie wtórne oraz P/U/I
każdego pola. Sprawdzamy przyszłe różnice dla 10, 30, 60, 120, 180, 300 i 600 s.
Predyktory dostępne w chwili `t` to historia elektryczna, kontekst procesu,
faza wszystkich sześciu strzepywaczy i czas dobowy. W wariancie rozszerzonym
dodajemy wyłącznie bieżący i przeszły poziom, trend oraz różnice pyłu.

## Porównanie modeli

Podstawą jest Ridge/ARX z normalizacją cech, bez strojenia hiperparametrów.
Modele bazowy i rozszerzony używają dokładnie tych samych znaczników czasu i
chronologicznych foldów D1–D3. Raportujemy MAE, RMSE, R² i ich zmianę po dodaniu
pyłu, oddzielnie dla każdego wyniku i horyzontu. Stabilność sprawdzamy przez
zgodność znaku i zakres zmian wyników między foldami, nie przez wybór najlepszego
folda.

## Innowacja i zdarzenia

Innowacja pyłu to bieżący pył minus predykcja Ridge oparta na jego przeszłości,
procesie i rappingu, dopasowana wyłącznie na treningu folda. Lokalne projekcje
warunkują przyszłą zmianę elektryczną na historię elektryczną, proces, rapping
i tę innowację. Współczynnik jest opisowy; przedziały niepewności są bootstrapem
całych dni oceny.

Epizod dodatni/ujemny zaczyna się przy pierwszym przekroczeniu odpowiednio 95./5.
percentyla 60-sekundowej zmiany pyłu ustalonego na treningu. Jednostką analizy
jest start epizodu. Odpowiedź badamy w pełnych oknach 0–10 min: w całej próbie,
poza aktywnymi oknami któregokolwiek strzepywacza oraz w stabilnym podzbiorze
procesu. Placebo przesuwa cechy pyłu wewnątrz dnia o 30 min i nie może dawać
podobnego przyrostu jakości.

## Granice interpretacji

Potwierdzone mogą być kolejność sygnałów, przyrost informacji, opóźnienie,
asymetria i stabilność opisowych zależności. Hipotezami pozostają: wejście
pyłomierza do regulatora, ECO, nadmierne utrzymanie mocy i oszczędność energii.
Alternatywami są harmonogram rappingu, wspólne wymuszenie procesowe, odpowiedź
elektryczna na własności pyłu, filtracja/transport pyłomierza i ukryte limity.
