# Walidacja audytu — 2026-09-10

## Zakres wykonania

- 8/8 testów `unittest` zakończonych powodzeniem.
- Wszystkie komórki kodu siedmiu notebooków kompilują się; struktura notebooków
  przechodzi walidację nbformat.
- `pip check`: brak niespełnionych zależności. Lista wersji:
  `audit_environment.txt`. Środowisko audytu różni się od historycznego locka.
- 01: pełny kod, model po korekcie i kontrola z przeciekiem na identycznych wierszach.
- 04: analiza zdarzeń, profile i nowe cechy rappingu; bez modeli na starych FE 02/03.
- 05 i 06a: pełny kod, włącznie z diagnostyką energii. Scenariusze roczne mają NaN
  zgodnie z wyłączoną ekstrapolacją, nie z powodu błędu wykonania.
- 06b: pełny kod w osobnym wywołaniu `--only 06b` po poprawie masek.
- Kod działał w trybie Agg. Wykresy zostały obliczone, ale nie przeprowadzano
  wizualnej oceny wykresów; ostrzeżenia o braku interaktywnego okna są oczekiwane.
- Wyniki, manifest wejść, SHA-256 i logi komórek są lokalne:
  `data/processed/audit_v2/results.json`, `*_execution.log`, tabele CSV i parquet.
  Kontrola integralności wejść po przeliczeniu: **bez zmian**.

## Wyniki opisowe nowego przeliczenia

Wartości poniżej to agregaty kontrolne do kontynuowania prac; nie stanowią
zatwierdzonej oceny przyczynowej, oszczędności ani wyników publikacyjnych.

**Dane modelowe:** 210 644 wiersze, 76 kolumn, indeks uporządkowany i unikalny,
brak NaN w tym istniejącym pliku clean. Rozpiętość 32 dni, ciągłe pokrycie
24,37928 dnia, 76,1853%, sześć luk. Wcześniejsze czyszczenie mogło usunąć
niekompletne wiersze; brak NaN w clean nie oznacza kompletnej rejestracji procesu.

**01:** 174 080 wierszy treningowych i 43 521 testowych.

| Wariant na identycznych wierszach | MAE | R² |
|---|---:|---:|
| Historyczna średnia bez bieżącego targetu | 1,39391 | 0,63421 |
| Kontrola z przywróconą przeciekającą średnią | 1,34351 | 0,66045 |

Kontrola przywraca tylko przeciekającą średnią targetu; pozostałe naprawy i podział
pozostają wspólne. To nie jest dokładna reprodukcja dawnego środowiska.

**04:** dla `008B05154` 423 pełne profile [−2,+5] min. Mediana profilu:
baza 11, pik 42, wzrost 31 mg/Nm³, czas do piku 1,1667 min.
To zachowuje wcześniejszą obserwację opisową, bez dowodu wyłącznej przyczynowości.

**06a:** 423 obserwowane starty, 1 odrzucony z powodu niepełnego okna,
0 odrzuconych przez regułę nakładania tego samego tagu, 422 zaakceptowane;
411 w podzbiorze filtrowanym „typical”. Dla 3-minutowych różnic maksimum korelacji:

| Relacja | Lag | Korelacja | Liczba par |
|---|---:|---:|---:|
| Δpył(t), ΔP(t+lag) | +1,3333 min | 0,56734 | 210 462 |
| Δpył(t), ΔU(t+lag) | +1,3333 min | 0,55571 | 210 462 |

Dodatni znak oznacza, że zmiana pyłu poprzedza zmianę elektryczną.
Nie wyznaczono przedziałów ufności; autokorelacja i wspólne wymuszenia nadal
ograniczają interpretację.

W „typical” mediana dodatkowej energii wynosi 1,10357 kWh/zdarzenie.
Mediana wskaźnika współwystępowania: 0,74402 kWh; mediana ścisłego ogona:
0,14099 kWh. Definicja ogona wymaga ostatniego przekroczenia pyłu i obserwowanego
powrotu przez co najmniej 60 s, więc liczby te opisują różne zjawiska.
Wszystkie 422 zdarzenia: 394 ze wzrostem i pełnym powrotem pyłu, 10 ze wzrostem
bez potwierdzonego powrotu, 18 bez wzrostu ponad próg.

| Próba | Dodatnia energia ponad bazą | Energia ścisłego ogona |
|---|---:|---:|
| Wszystkie zaakceptowane zdarzenia | 662,90258 kWh | 284,71779 kWh |
| „Typical” (filtr po wyniku) | 543,19892 kWh | 208,50753 kWh |

To sumy zdarzeń w obserwowanej próbie, **nie miesięczne lub roczne oszczędności**.
Sprawdzono zgodność sum podpisanych wkładów sekcji z energią całkowitą,
energię ogonową nie większą od dodatkowej i czas przekroczeń nie dłuższy niż 15 min.

## Pozostałe ograniczenia

Nie przeliczono modeli 02/03 ani modeli 04 opartych na ich cechach; wymagają
oddzielnego audytu dostępności sygnałów i wspólnego splitu. Nie odtwarzano ZIP → clean.
Nie wykonano testów na instalacji, walidacji jednostek przez technologa,
analizy wszystkich nakładających się strzepywaczy, analizy czułości progów
ani estymacji niepewności. Szczegółowy następny etap: `research_plan.md`.
