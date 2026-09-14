# H3: sprawdzenie uogólniania hybrydy ESP

Stan: 2026-09-14. Ten raport sprawdza hipotezę H-G z
[hybrid_esp_methodology.md](hybrid_esp_methodology.md) po pilotażu H2/D1
opisanym w [hybrid_esp_validation.md](hybrid_esp_validation.md). Jest to wynik
rozwojowy na już oglądanym miesiącu danych, a nie niezależna walidacja ani
cyfrowy bliźniak ESP.

## Zamrożony test i kontrola danych

Uruchomiono tę samą, bez strojenia konfigurację M0--M3 na D1, D2 i D3. M1 to
model danych oparty na identycznym zbiorze cech, a M3 to ograniczony rdzeń
fizyczny z chronologiczną korektą reszt. Do fitu i kalibracji usuwano trzy
wcześniej zdefiniowane reżimy: obciążenie powyżej P80, przepływ powyżej P80 i
obciążenie poniżej P20. Progi wyznaczono wyłącznie w outer train. Wokół każdego
wyłączonego epizodu usuwano z treningu i kalibracji bufor 1 020 s, aby historia
rappingu nie przechodziła przez lukę treningową.

Wszystkie obliczenia zachowywały ciągłe segmenty czasu. Test syntetyczny
potwierdza, że bufor nie przechodzi przez lukę znaczników; wcześniejsze testy
potwierdzają przyczynowość jąder, bilans, ograniczenia i brak wpływu przyszłej
modyfikacji na wcześniejszy fit. Smoke oraz pełne H3 ukończyły się poprawnie.
SHA-256 wejścia przed i po pełnym przebiegu jest identyczne:
`686910605846534322f45d196d602bcf98fe256a93fda94edc429c081e629260`.

Pełny przebieg trwał 164,0 s. Końcowy RSS procesu wyniósł 0,36 GiB, wolny RAM
5,65 GiB, a wolny dysk 13,08 GiB. Lokalny katalog wyników zawiera wyłącznie
manifest i agregaty; nie wersjonowano danych przemysłowych, modeli ani
predykcji jednostkowych.

## Wynik głównego testu H-G

Tabela pokazuje MAE na rzeczywistych, przyszłych originach należących do
wyłączonego zakresu. Dodatnia zmiana oznacza pogorszenie M3 względem M1.
Każdy kwalifikujący się test ma co najmniej 300 originów i trzy daty oceny.

| Fold | Wyłączony reżim | Originy | MAE M1 | MAE M3 | Zmiana M3 względem M1 |
| --- | --- | ---: | ---: | ---: | ---: |
| D1 | obciążenie >P80 | 7 005 | 2,166 | 3,254 | +50,2% |
| D1 | przepływ >P80 | 8 429 | 1,889 | 2,612 | +38,3% |
| D1 | obciążenie <P20 | 2 650 | 1,471 | 1,744 | +18,5% |
| D2 | obciążenie >P80 | 2 675 | 3,737 | 4,069 | +8,9% |
| D2 | przepływ >P80 | 4 286 | 3,290 | 3,585 | +9,0% |
| D2 | obciążenie <P20 | 3 538 | 2,258 | 3,169 | +40,3% |
| D3 | obciążenie >P80 | 8 090 | 6,147 | 7,075 | +15,1% |
| D3 | obciążenie <P20 | 12 985 | 2,412 | 3,347 | +38,8% |

W D3 dla przepływu >P80 po buforowaniu pozostała tylko jedna data z danymi w
dwudniowej części kalibracyjnej. Nie zastąpiono jej inną datą i nie zmieniono
reguły po wyniku: test oznaczono jako **niewystarczające pokrycie**. Nie jest
to ani sukces, ani porażka H-G.

M3 przegrał ze wspólnym baseline M1 we wszystkich ośmiu kwalifikujących się
testach. W trzech testach D1 dolna granica 95% bootstrapu po pełnych datach
dla `MAE(M1) − MAE(M3)` jest ujemna także wewnątrz wyłączonego reżimu:
od −1,198 do −0,596 mg/Nm³ dla wysokiego obciążenia i przepływu oraz
−1,032 mg/Nm³ dla niskiego obciążenia. W D2 część przedziałów obejmuje zero,
ale kierunek punktowy nadal jest niekorzystny; dla niskiego obciążenia dolna
granica wynosi −1,830 mg/Nm³. W D3 przedziały dla wysokiego i niskiego
obciążenia są całkowicie ujemne, odpowiednio [−1,317; −0,419] i
[−1,253; −0,664] mg/Nm³.

## Wsparcie i granica interpretacji

W wyłączonych originach M3 oznaczył 73,1--86,1% jako bliskie treningowi,
1,2--3,1% jako graniczne oraz 11,9--25,0% jako poza wsparciem. Słaby wynik nie
ogranicza się zatem do prostego odrzucenia wszystkich nowych stanów. Jednocześnie
rdzeń w każdym wykonanym teście miał 12--16 parametrów na granicach ograniczeń.
To wraz z brakiem geometrii, pyłu na wlocie i potwierdzonego sterowania nadal
uniemożliwia interpretację parametrów jako właściwości instalacji.

**Potwierdzona obserwacja:** w tej zamrożonej implementacji prosty model danych
uogólnia się na trzy wyłączenia co najmniej tak dobrze jak hybryda, a w tym
zbiorze wyraźnie lepiej. **Nie wynika z tego**, że fizyka elektrofiltru jest
błędna, ani że model danych reprezentuje mechanizm. Wynik odrzuca tylko
praktyczną hipotezę przewagi tego rdzenia + korekty nad M1 w dostępnym archiwum.

## Decyzja i dalszy zakres

Bramka G2 nie jest spełniona: nie ma dodatniej mediany poprawy dziennego MAE,
nie ma dodatniego wyniku w dwóch foldach, a pełne i wyłączone MAE pogarsza się
zamiast poprawiać. H4 pozostaje zamknięte. Nie wolno używać M3 do scenariuszy
nastaw, optymalizacji energii, oszczędności ani poszerzania bezpiecznej
przestrzeni pracy ESP.

Pozostałe ablacje H3 służące wyłącznie diagnostyce identyfikowalności nie będą
traktowane jako poszukiwanie korzystnego modelu po negatywnej bramce G2. Można
je wykonać później tylko jako osobny, opisowy test H-U z uprzednio ustalonym
zakresem. Sensowny następny etap doktoratu to wykorzystanie wyniku jako
negatywnej granicy modelowania hybrydowego oraz wybór nowego pytania badawczego
albo pozyskanie brakujących pomiarów instalacyjnych.
