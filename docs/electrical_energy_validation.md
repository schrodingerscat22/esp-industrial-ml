# E1: audyt sygnałów elektrycznych i porównywalności energetycznej

Stan: 2026-09-12. Kod: `scripts/run_electrical_energy_audit.py`; lokalne,
ignorowane artefakty: `data/processed/electrical_energy_v1/`. Ten raport opisuje
wynik rozwojowego miesiąca danych. Nie jest rekomendacją zmiany nastaw, dowodem
oszczędności ani pomiarem rezystywności pyłu.

## Zakres i odtwarzalność

Przetworzono `df_model_clean_v1.parquet`: 210 642 próbek co 10 s, 32 dni
rozpiętości kalendarzowej, 24,37882 dnia rzeczywistego pokrycia i osiem luk.
SHA-256 wejścia przed i po analizie był identyczny:
`686910605846534322f45d196d602bcf98fe256a93fda94edc429c081e629260`.
Surowych ani przetworzonych danych, modeli i wyników jednostkowych nie dodano do
Git. Pełny przebieg E1 zużył maksymalnie 0,85 GB śledzonej pamięci.

Każda cecha czasowa i okno zdarzenia wymaga ciągłych obserwacji co 10 s. Zdarzenia
analizowano w oknie [−5, +15] min, a bloki energii miały dokładnie 10 min i
liczyły całkę z 60 lewych punktów siatki. Dopasowanie nie używało pyłu.

## Potwierdzone obserwacje

| Wielkość | Pole 1 | Pole 2 | Pole 3 |
| --- | ---: | ---: | ---: |
| Poprawne U i I | 100% | 100% | 100% |
| Mediana U/I [MΩ] | 0,1605 | 0,1340 | 0,1250 |
| 5–95 percentyl U/I [MΩ] | 0,1554–0,1661 | 0,1275–0,1362 | 0,0942–0,1296 |
| Udział niezerowych iskier | 0,643% | 0,040% | 0,000% |
| Korelacja mocy tagu z U×I | 0,9994 | 0,9995 | 0,9996 |
| MAE mocy tagu względem U×I [kW] | 0,130 | 0,140 | 0,148 |

Są to wiarygodne argumenty, że archiwalne sygnały elektryczne nadają się do
opisu stanu. Iloraz U/I pozostaje **pozorną rezystancją**, a nie rezystywnością
pyłu ani pomiarem wejściowej energii zasilacza.

Znaleziono 13 409 kompletnych okien startu sześciu sygnałów rappingu. Profil
mocy po starcie silnie różni się między tagami: dla rappingu kolektora pola 3
(`008B05154`, 421 okien) mediana zmiany mocy 0–5 min wyniosła +9,25 kW, a
mediana U/I pola 3 zmieniła się o −0,0325 MΩ. Pozostałe tagi nie wykazały
porównywalnego medianowego skoku mocy w tym prostym podsumowaniu. To opis
współwystępowania; wszystkie okna krytycznego tagu mają inny start rappingu w
oknie [−5, +15] min, dlatego nie identyfikuje to samodzielnego efektu rappingu.

W analizie dziennej, po wyłączeniu fazy rappingu z czasu od poprzedniego startu
poniżej 15 min, mediany korelacji U/I pola 3 z temperaturą spalin, obciążeniem
i wilgotnością wynoszą odpowiednio −0,333, −0,220 i −0,207 (26 dni). Zakresy
między dniami są szerokie, więc potwierdzają jedynie związek opisowy wymagający
dalszej kontroli kontekstu, a nie stabilne prawo procesu.

## Porównywalność energetyczna i decyzja

Z 3 505 kompletnych bloków po zastosowaniu poziomu 3 (ten sam stan wszystkich
sześciu rappingów, zgodne stany palników oraz warunki procesu) nominalne
dopasowanie przy tolerancji 1 i różnicy mocy co najmniej 2 kW nie dało ani jednej
pary. Nawet przy dwukrotnie łagodniejszych tolerancjach uzyskano tylko osiem
par, czyli 0,46% godzin kwalifikowanych. Próg decyzji wymagał co najmniej 30
par, co najmniej trzech dni po każdej stronie i minimum 10% pokrycia.

**Decyzja E1: B — istnieje użyteczny sygnał opisujący stan elektryczny, ale nie
ma pokrycia potrzebnego do obserwacyjnego benchmarku energii.** Nie raportujemy
wpływu dodatkowych kW na pył ani potencjalnej oszczędności. Czułość progu
różnicy mocy 1/2/3 kW przy poziomie 3 i łagodniejszej tolerancji 2 dała kolejno
10/8/3 pary (0,57/0,46/0,17% godzin); przy tolerancji nominalnej 1 nie było par
dla żadnego progu. Pełna tabela pozostaje lokalnie w `support_summary.csv`.

## Hipotezy i braki wiedzy o instalacji

- Hipoteza: model stanu zależny od procesu może wykrywać odstępstwa od typowej
  charakterystyki U–I. Nie zweryfikowano jeszcze jego przyrostu informacji ani
  użyteczności dla obsługi.
- Hipoteza: niższa moc przy tej samej jakości odpylania może być możliwa w części
  stanów. Dane nie zawierają porównywalnych kontrfaktycznych okresów, więc nie
  jest to wynik E1.
- Nieznane pozostają nastawy i tryby regulatora, granica fizyczna tagów mocy,
  opóźnienie oraz geometria pyłomierza, a także właściwości pyłu na wlocie.

## Następny krok

Nie przechodzimy do optymalizacji nastaw. Jeżeli temat ma być kontynuowany bez
danych z instalacji, można wykonać mały E2: sprawdzić na osobnym czasie, czy
proces i cykl rappingu wyjaśniają U/I lepiej niż sama historia U/I, oraz czy
reszty są stabilne między dniami. Wynik E2 byłby monitorem diagnostycznym, nie
sterownikiem energetycznym. Badanie oszczędności wymaga później archiwum nastaw
lub bezpiecznego, zatwierdzonego eksperymentu zmiany sterowania.
