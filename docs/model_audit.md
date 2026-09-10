# Audyt modeli 02/03 — 2026-09-10

## Cel i kontrakt tego etapu

Eksploracyjny **online nowcasting**: przewidujemy y(t), zakładając dostępność
sygnałów procesowych x(t) oraz — tylko w wariancie z historią pyłu — pomiarów
pyłu do t−10 s. To nie jest prognoza na przyszłe minuty. Znaczniki rejestracji
nie dowodzą dostępności sygnału w systemie online; synchronizacja, opóźnienia
i sens poszczególnych tagów nadal wymagają potwierdzenia z technologiem.

Kontynuacja commita `3189508` na `codex/methodology-audit`. Użytkownik zezwolił
na commit i push kodu, testów i dokumentacji; dane i wyniki jednostkowe pozostają
lokalne. Nie modyfikujemy raw ani dotychczasowych artefaktów v1/v2.

## Ustalenia audytu historycznych notebooków

| Miejsce | Ustalenie | Wpływ na dostępne dane / działanie |
|---|---|---|
| 02, komórka 1 | Pierwszy parquet z glob zamiast jawnego wejścia | Naprawione: dataset_clean.parquet |
| 02, komórka 46 | ffill, potem bfill małych braków bez limitu czasowego | Ryzyko użycia przyszłości i nieaktualnych stanów. W danych: 50 brakujących komórek w 2 wierszach po filtrze obciążenia; ffill wypełniał wszystkie, bfill faktycznie 0 |
| 03, komórka 6 | Segmenty dopiero dla luk >60 s | Podatność na niepoprawne lagi/okna przy lukach 20–60 s. W dotychczasowym clean brak takich luk; test syntetyczny potwierdza naprawę |
| 03, komórki 7/11/17/23 | Target wykluczony z wejść, jego lagów, rolling i diff | Nie potwierdzono bezpośredniego przecieku y(t) analogicznego do 01 |
| 03, komórka 16 | Wybór analogowych sygnałów przez nunique na całym zbiorze | Schemat cech teraz dopasowywany wyłącznie w treningu każdego podziału |
| 03, komórki 17/23 | Rolling i diff zawierają aktualny sygnał procesowy | Dopuszczalne przy kontrakcie x(t), nie automatycznie przy prognozie lub opóźnionej dostępności |
| 03, komórki 26/27 | segment_id początkowo w X, usunięty przed treningiem | Nie był wejściem modelu przy wykonaniu notebooka po kolei; nowy moduł nigdy go nie emituje |
| 03, komórki 47–54 | Wiele wariantów ocenianych na jednym teście; ręcznie wpisany baseline z 01 | Baseline dodatkowo zawierał przeciek. Zastąpiono nowym persistence i identycznymi wierszami oceny |
| 02/03, zapisy | Nadpisywanie artefaktów v1 | Nowe zapisy wyłącznie do ignorowanego audit_v3 |

Numery odnoszą się do wersji przed tym etapem, indeks od zera.
Notebook 02 zachowuje część opisową i historyczny klasyfikator, ale usuwa imputację.
03 jest teraz krótkim interfejsem do testowalnego modułu i skryptu. Historyczny kod
pozostaje w Git; usunięto outputy notebooków, w tym dawne metryki.

## Nowy eksperyment

Wejście: `dataset_clean.parquet` i istniejąca wersja `tag_classification_v1.xlsx`.
75 tagów oznaczonych `input`; target sprawdzany osobno. Metadane są traktowane
jako istniejący kontrakt — ich wcześniejszy sposób przygotowania nie jest niezależny
od całej próby. Nie tworzymy ich automatycznie na nowo w eksperymencie.
Wiersze z NaN/inf w wybranych sygnałach lub target są usuwane, bez imputacji.
Powstałe luki przerywają wszystkie cechy czasowe.

Granice czasu ustalone na uporządkowanych wierszach clean **przed generacją cech**:

1. Trening pierwsze 40%, walidacja 40–60%.
2. Trening pierwsze 60%, walidacja 60–80%.
3. Trening pierwsze 80%, test ostatnie 20%.

Granice są timestampami zapisanymi przed dopasowaniem w `design.json`.
Schemat analogowych sygnałów (`nunique > 10`) dopasowujemy oddzielnie na treningu.
Nie ma strojenia, wyboru wariantu ani early stopping na teście. Dwa XGBoost mają
identyczne, z góry ustalone parametry: 200 drzew, głębokość 4, learning_rate 0,05,
subsample/colsample 0,8, seed 42, histogramy, cztery wątki.

Proces: wartości bieżące; lagi 1/3/6/12/30/60/180 próbek dla wszystkich wejść;
rolling mean/std 6/30/60/180 i diff 1/6/30/60 dla analogowych wejść.
Historia pyłu: takie same lagi; rolling wyłącznie na `y.shift(1)`;
różnice `y(t−10 s) − y(t−(n+1)×10 s)`. Dane cech float32.

W każdym podziale wszystkie trzy modele używają tych samych wierszy oceny,
z pełną historią cech procesowych i pyłu. Persistence = y(t−10 s).
Wymóg wspólnych wierszy jest konserwatywny dla modelu bez pyłomierza: sam mógłby
działać na większej próbie. Rapping jest warstwą oceny, a nie filtrem usuwającym piki.

Nie stosujemy sztucznego odstępu 30 min między treningiem i oceną: horyzont
etykiety wynosi zero, historia wcześniejszych obserwacji jest legalnie dostępna
w zadeklarowanym online nowcastingu. Oceniane etykiety nie są używane w fit.
Historia pyłu jest aktualizowana rzeczywistymi pomiarami w okresie oceny; to nie
jest rekurencyjna prognoza bez dostępu do kolejnych pomiarów.

**Okres testowy był już oglądany w poprzednich analizach.** Wyniki pozostają
eksploracyjne. Do zatwierdzenia publikacyjnego potrzebny jest nowy, nieoglądany
okres i zamrożony wcześniej protokół. Sama poprawa splitu nie usuwa historycznej
adaptacji decyzji do danych.

## Ocena i odtwarzanie

MAE, RMSE, bias, R² na każdym podziale. Na teście dodatkowo zakresy pyłu,
okno 0–5 min po krytycznym rappingu, poza nim, dni i kwartyle obciążenia
z granicami dopasowanymi na treningu. Puste warstwy raportują n=0 i brak metryk.
Bootstrap parowany 1000 losowań całych obserwowanych dni ocenia MAE i różnicę
wobec persistence; zachowuje próbki wewnątrz dnia. Przy niewielu dniach, niepełnych
dniach i dłuższej zależności czasowej są to zakresy opisowe, nie rozstrzygający test.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/run_model_audit.py
```

Lokalnie w `data/processed/audit_v3/`: projekt eksperymentu, report.json z hashami
wejść/kodu i wersjami, metrics.csv, stratified_metrics.csv, predykcje każdego
podziału, modele końcowe, importance, X_process, X_dust_history i y w parquet.
Pliki te nie są dodawane do Git. Wyniki agregatowe: `model_validation.md`.

## Następne rozstrzygnięcia

1. Wybrać zastosowanie i ewentualny horyzont prognozy. Persistence 10 s może być
   bardzo silnym punktem odniesienia; słabszy model procesowy nie jest automatycznie
   bezużyteczny jako soft sensor, ale jego cel musi być jasno rozdzielony.
2. Nowe dane do zamrożonego testu; lineage ZIP → clean i jakość pomiarów.
3. Fizyczna dostępność sygnałów, ablacją usunąć współbieżne kanały emisyjne,
   jeśli nie są dostępne w docelowej chwili lub systemie.
4. Dopiero potem strojenie w walidacji kroczącej i badanie ECO/kontrfaktycznej
   oszczędności. Obecne wyniki nie uprawniają do zmiany nastaw.
