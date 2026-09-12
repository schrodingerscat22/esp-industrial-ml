# E: ocena energetyczna ESP z charakterystyk elektrycznych i danych procesu

Stan: 2026-09-12. **E1 wdrożono i przeliczono; decyzja: B.** Wyniki i ograniczenia
są w [electrical_energy_validation.md](electrical_energy_validation.md). E2 nie
jest jeszcze wdrożone. Instrukcja implementacyjna E1 pozostaje w
[electrical_energy_handoff.md](electrical_energy_handoff.md).
Dokument jest odrębnym kierunkiem energetycznym. Nie zmienia definicji ani
wyników F1–F3 z [forecasting_methodology.md](forecasting_methodology.md).

## 1. Decyzja i cel użytkowy

Warto wykonać ograniczony audyt E1. Podstawy fizyczne są przekonujące, a w danych
istnieją napięcia, prądy, wilgotność, temperatury i wskaźniki pracy procesu.
**Nie ma jeszcze podstaw do obietnicy oszczędności ani zbudowania regulatora.**

Rekomendowane pytanie badawcze:

> Czy uwzględnienie warunków procesu pozwala rozpoznać zmiany elektrycznej pracy
> ESP oraz wskazać powtarzalne, porównywalne stany o mniejszym zużyciu energii,
> które warto następnie zweryfikować jako kandydatów do zmiany sterowania?

Docelowy odbiorca: osoba oceniająca pracę ESP i ustawienia jego zasilaczy.
Najpierw wynikiem ma być mapa warunków pracy i uzasadniona decyzja o wykonalności.
Późniejszym wynikiem może być monitor odstępstw od oczekiwanej charakterystyki
elektrycznej lub narzędzie wskazujące okresy do przeglądu energetycznego.
Rekomendacje nastaw wymagają dodatkowego poziomu dowodów.

Ocena potencjału na dziś:

| Zastosowanie | Ocena | Główna przeszkoda |
| --- | --- | --- |
| Opis zmian U–I na tle procesu i cykli | Wykonalny pierwszy etap | Luki, kwantyzacja, nakładanie zdarzeń |
| Monitor stanu elektrycznego zależny od procesu | Uzasadniona hipoteza | Trzeba wykazać przyrost informacji i użyteczność odstępstw |
| Ranking okresów do audytu energetycznego | Warunkowo wykonalny | Porównywalność i rzeczywista zmienność mocy |
| Dobór oszczędnych nastaw | Niepotwierdzony potencjał | Nieznane polecenia regulatora i skutki alternatywnych działań |
| Pomiar rezystywności pyłu lub przewidywanie pojedynczych iskier | Nieuzasadnione na obecnym zbiorze | Brak pomiaru referencyjnego i szybkich przebiegów |

Samo wyliczenie U/I, wykresy korelacji lub zastosowanie XGBoost nie stanowią
samodzielnego wkładu doktorskiego. Wartość naukową trzeba oprzeć na weryfikowalnym
przyroście informacji, odporności na zmianę warunków oraz granicach identyfikacji.
Bez nowych danych lub eksperymentu zakres wniosków pozostanie obserwacyjny.

## 2. Co rzeczywiście oznacza U/I

Rezystywność materiału `rho` ma jednostkę Ω·m lub Ω·cm. W idealnym jednorodnym
przewodniku `R = rho * L / A`. Zmiana grubości warstwy zmienia jej opór nawet
przy niezmiennej rezystywności. W ESP dochodzą nieliniowy ulot, ładunek
przestrzenny, gaz, geometria, osad i działanie regulatora.

Dla wartości wtórnych zapisujemy:

- `R_app_Mohm = U_kV / I_mA` — iloraz zarejestrowanych wartości, pozorna rezystancja;
- `G_app_uS = I_mA / U_kV` — odwrotność; domyślnie nie dublować obu cech w modelu;
- `P_UI_kW = U_kV * I_mA / 1000` — kontrolny iloczyn rejestrowanego U oraz I.

Nie jest to pomiar rezystywności pyłu, rezystancja różniczkowa dU/dI ani pełna
impedancja z informacją fazową. Iloczyn średnich U i I nie musi być średnią
mocą chwilową, zwłaszcza przy zasilaniu impulsowym. Zgodność z tagiem mocy
potwierdza zgodność rejestracji, a nie niezależny pomiar mocy pobieranej z sieci.

Pył zawieszony, osad na elektrodach i pył zmierzony na wylocie to różne wielkości.
Wpływ warstwy oraz ładunku cząstek na charakterystykę U–I ma podstawy fizyczne,
ale nie daje uniwersalnej reguły „więcej pyłu = większe/mniejsze U/I”.
[Model fizyczny EPA, rozdział o charakterystykach U–I](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=9101GJDP.TXT).

Temperatura, wilgotność i skład gazu mogą zmieniać własności osadu. Niska i wysoka
rezystywność mogą ograniczać odpylanie przez odmienne mechanizmy; duży prąd nie
jest samodzielnym dowodem dobrego odpylania.
[EPA, rozdział o ESP, sekcje 3.1.2.1 i 3.2.5](https://www.epa.gov/sites/default/files/2020-07/documents/cs6ch3.pdf).

U/I nie wnosi nowego pomiaru ponad U oraz I. Może być przydatną reprezentacją
ułatwiającą modelowanie i interpretację. Poprawy po dodaniu ilorazu nie wolno
przedstawiać jako odkrycia nowej informacji fizycznej.

## 3. Co robią już regulatory i gdzie szukać wkładu

Automatyczne dostosowywanie zasilania do warunków wyładowania jest istniejącą
techniką. Także optymalizacja mocy ESP połączona z systemem procesowym występuje
w ofercie przemysłowej: [Valmet ESP i Power Optimization](https://www.valmet.com/energyproduction/air-emission-control/esp/valmet-esp/).
To dowód istnienia zastosowania; deklaracje dostawcy nie są wynikiem dla naszej instalacji.

Dobór napięć wielu pól przy ograniczeniu stężenia wylotowego był już przedmiotem
badań: Li, Shao, An i Xu, *Energy-saving optimal control for a factual
electrostatic precipitator with multiple electric-field stages based on GA*,
Journal of Process Control 23(8), 1041–1051, 2013.
[Strona wydawcy i abstrakt](https://www.sciencedirect.com/science/article/pii/S0959152413001297).
Przejrzano opis/abstrakt; nie wykonano pełnej reprodukcji ani systematycznego
przeglądu nowości. Nie twierdzimy, że proponowany kierunek jest pierwszy.

Potencjalny wkład naszego badania to ocena, kiedy dane procesowe wyjaśniają
zmiany U–I ponad fazę cyklu i historię elektryczną, oraz kiedy archiwum regulatora
pozwala w ogóle porównać warianty energetyczne. Przyszła aplikacja może działać
jako wolniejsza warstwa nadzoru nad istniejącymi zasilaczami. Dane co 10 s
nie uzasadniają zastępowania ich szybkiej ochrony przed przeskokiem.

## 4. Ustalenia rozpoznawcze i korekta wcześniejszej interpretacji

Wejście: `data/processed/audit_v3/df_model_clean_v1.parquet`, 210 642 wiersze,
76 kolumn, 32 dni rozpiętości, 24,37882 dnia pokrycia, 8 przerw w siatce 10 s.
SHA-256 i szczegóły lokalnie:
`data/processed/energy_idea_review_20260912/preflight.json`.
Hash wejścia przed i po sprawdzeniu był identyczny. Nie trenowano modeli.

To dane po wcześniejszym czyszczeniu. `dataset_clean.parquet` ma 217 781
wierszy i 437 wykrytych startów krytycznego rappingu; analizowane wejście ma
423 starty. Nie mieszać mianowników. E1 musi porównać selekcję między wersjami.

| Obserwacja w bieżącym wejściu | Znaczenie |
| --- | --- |
| Mediany U/I: 0,1605 / 0,1340 / 0,1250 MΩ | Istnieje czytelny sygnał elektryczny, osobny dla pól |
| Przeskoki niezerowe: 0,643% / 0,040% / 0% próbek | Brak podstaw do modelu granicy iskrzenia strefy 3; zero nie dowodzi braku iskier |
| Trzy najczęstsze wartości prądu pokrywają ok. 95% próbek pola 2 i 93% pola 3 | Zmienność może być ograniczona regulacją lub rejestracją; nastawy są nieznane |
| Korelacja tagów mocy z U*I/1000: 0,9994–0,9996 | Moc i U–I są prawie algebraicznie zależne |
| Łączna moc trzech tagów: mediana 38,3 kW; P5–P95 37,4–47,0 kW | Zróżnicowanie istnieje, lecz obejmuje zaburzenia cykliczne |
| Poza ±15 min od krytycznego startu: P5–P95 37,4–39,5 kW | Większość zwykłej pracy ma wąski zakres mocy |

Ostatnia maska jest retrospektywna, obejmuje tylko krytyczny tag i wymaga
co najmniej 15 min obserwacji do obu końców segmentu. Nie oznacza „bez rappingu”.

**Korekta wcześniejszej odpowiedzi w rozmowie:** zbiorcza mediana próbek po
strzepywaniu nie jest medianą sparowanych zmian zdarzeń. W 421 kompletnych
oknach [−5,+15] min, z własną bazą każdego zdarzenia [−5,−1] min oraz medianą
U/I w [0,+5] min, mediana zmiany procentowej wynosi:

| Pole | Mediana sparowanej zmiany U/I |
| --- | ---: |
| 1 | 0,0% |
| 2 | −2,4% |
| 3 | −26,1% |

Wcześniejsze około −21% dla pola 2 opisywało różnicę agregatów próbek, a nie
typową zmianę zdarzenia. Nie używać tej liczby jako efektu strzepywania.
Odrzucono 2 z 423 startów za niepełne okno. Spadek U/I pola 3 w chwili
zaobserwowanego piku pyłu wystąpił w 88,1% zaakceptowanych okien. Jest to
statystyka po wyborze chwili piku, wyłącznie retrospektywna.

**W każdym z 421 okien wystąpił start przynajmniej jednego innego strzepywacza.**
Nie oznacza to, że wszystkie zdarzenia nakładają się dokładnie w chwili piku;
oznacza brak izolowanych okien [−5,+15] przy takiej regule. Efekt pola 2 lub 1
nie może być automatycznie przypisany strzepywaniu pola 3.

Dotychczasowa energia ponad bazą i energia ogonowa z 06a pozostają opisami
przebiegów, a nie oszczędnością ani jej górną granicą. Analizy nie wykazały,
że zmniejszenie mocy utrzymałoby emisję. Patrz [methodology_audit.md](methodology_audit.md).

## 5. Połączenie z posiadanymi sygnałami procesu

Nazwy i jednostki poniżej pochodzą z lokalnego `tag_mapping.csv`. Opis tagu
jest dowodem znaczenia w metadanych; nie potwierdza kalibracji, położenia sondy
ani dostępności w rzeczywistym regulatorze.

| Grupa | Dostępne tagi | Rola i ograniczenie |
| --- | --- | --- |
| Obciążenie | `008A00936` — moc czynna generatora, MW | Wskaźnik obciążenia; nie bezpośrednia moc cieplna kotła ani strumień paliwa |
| Strumień spalin | `008A01353` — F spalin, tys. m³/h | Kontekst transportu i obciążenia gazem; nie zakładać Nm³/h, suchej bazy ani konkretnego toru |
| Powietrze do kotła L/P | `008A00910`, `008A00911`, Nm³/h | Suma i względna asymetria; nie zastępują pomiaru spalin |
| Temperatura spalin za OPP L/P | `008A00720`, `008A00728`, °C | Średnia, różnica L–P i zmiana w czasie; lokalizacja względem ESP wymaga weryfikacji |
| Wilgotność spalin | `008A02118`, % | Obecny w danych ważny kontekst własności pyłu/gazu; nie pomiar wilgotności samego osadu |
| Tlen przed OPP L/P | `008A00741`, `008A00742`, % | Kontekst spalania i asymetrii; sprawdzić ograniczenie zakresu, m.in. plateau 10% |
| Tlen BC1 | `008A01350`, % | Osobny pomiar; różnicy z O2 przed OPP nie nazywać ilością fałszywego powietrza bez zgodności baz i miejsc |
| SO2, NOx, CO | `008A01341`, `008A01343`, `008A01347`, mg/Nm³ | Wskaźniki zmian spalania/paliwa; SO2 nie jest pomiarem SO3 ani rezystywności, CO nie jest udziałem węgla w popiele |
| Ciśnienie spalin L/P | `008A00719`, `008A00727`, kPa | Średnia i asymetria; nie jest to spadek ciśnienia przez ESP |
| Kierownice i moce innych urządzeń | `008A00723`, `008A00731`; `016A00219`, `016A00396` | Dodatkowy kontekst transportu; tożsamość urządzeń dla tagów 016A pozostaje niepotwierdzona |
| Palniki olejowe | `008B01474`, `008B01479`, `008B01484`, `008B01489` | Flagi odmiennych warunków; nie utożsamiać każdego takiego okresu z awarią lub rozruchem |
| Temperatury lejów/rurociągów i grzałki | Tagi `008A02276`–`008A02287` oraz odpowiadające im statusy | Drugorzędny kontekst odbioru pyłu; brak poziomu zapełnienia i masy pyłu |
| Stężenie wylotowe pyłu | `008A01345`, mg/Nm³ | Wynik odpylania całego obserwowanego toru, nie stężenie wewnątrz każdej strefy |

Rejestr elektryczny:

| Wielkość | Pole 1 | Pole 2 | Pole 3 |
| --- | --- | --- | --- |
| U wtórne kVDC | `008A02289` | `008A02290` | `008A02291` |
| I wtórne mADC | `008A02267` | `008A02268` | `008A02269` |
| Moc zespołu kW | `008A02273` | `008A02274` | `008A02275` |
| Częstość przeskoków n/min | `008A02264` | `008A02265` | `008A02266` |
| Potwierdzenie załączenia | `008B05167` | `008B05173` | `008B05178` |
| Rapping zbiorczych | `008B05146` | `008B05150` | `008B05154` |
| Rapping ulotowych | `008B05131` | `008B05135` | `008B05139` |
| Prąd zespołu A, do audytu jednostek | `008A02270` | `008A02271` | `008A02272` |
| Napięcie zespołu V, do audytu jednostek | `008A02292` | `008A02293` | `008A02294` |

Nie odnaleziono w analizowanym schemacie jednoznacznych tagów zadanej wartości
U/I, limitów prądu/napięcia, stopnia zasilania impulsowego ani aktywnego trybu ECO.
Statusy załączenia trzech zasilaczy są stałe. Nie odtwarzać trybu ECO z nazwy
notebooka ani nie nazywać obserwowanego maksimum napięciem dopuszczalnym.

Brakuje także referencyjnej rezystywności, stężenia i granulometrii na wlocie,
składu popiołu oraz potwierdzenia geometrii i podziału strumieni A/B.
Sumę trzech tagów mocy nazywać **mocą trzech zarejestrowanych zespołów**,
dopóki nie potwierdzimy, że obejmuje cały właściwy ESP i jego tor spalin.

## 6. Hipotezy, pułapki i wynik negatywny

| Hipoteza | Jak ją sprawdzić | Wynik, który jej nie potwierdza |
| --- | --- | --- |
| H1: U–I niesie powtarzalny opis stanu procesu | Porównać dni, fazy wszystkich sześciu strzepywaczy i warunki gazowe | Zależność zanika po uwzględnieniu cyklu lub jednego dnia |
| H2: proces daje wartość ponad sygnały elektryczne i cykl | E2: identyczny model, originy i foldy, z procesem i bez niego | Brak stabilnej poprawy lub tylko odtwarzanie bieżącej algebry |
| H3: istnieją porównywalne stany o różnych kosztach energii | E1: pomiar zakresu wspólnych warunków i wielkości różnic mocy | Inna moc występuje wyłącznie przy innych warunkach/cyklach |
| H4: obniżenie energii zachowuje odpylanie | Nowy projekt interwencji lub uzasadniona identyfikacja przyczynowa | Samo dopasowanie obserwacji, SHAP lub symulacja modelu predykcyjnego |

Najważniejsza pułapka: działający regulator reaguje na zmianę procesu. Wysoki
pył i wysoka moc mogą mieć wspólną przyczynę; zwiększona moc może być potrzebna,
aby pył nie wzrósł jeszcze bardziej. Kolejność pików tego nie rozstrzyga.

Druga pułapka: `P = U*I`, `R = U/I`. Model P z bieżącym U i I albo model I z
bieżącym R i U rozwiązuje niemal tożsamość. To nie identyfikuje zapotrzebowania
na moc ani minimalnej energii. Diagnostyczny model `I | U, proces, cykl` może być
użyteczny, ale opisuje zachowanie przy obserwowanym sterowaniu.

Trzecia pułapka: pola pracują szeregowo, a dostępny pyłomierz mierzy wynik
zbiorczy. Nie zakładać ich niezależności ani przypisywać każdemu polu osobnej
sprawności odpylania. Równoczesne zmiany pól utrudniają rozdzielenie wkładów.

Jeżeli H3 nie ma wystarczających danych, zapisujemy „brak identyfikowalności
w archiwum”, a nie „regulator jest optymalny” ani „nie da się oszczędzać”.
Jeżeli H2 także nie zostanie potwierdzona, zatrzymujemy rozwój modeli tego
kierunku. Kolejny kosztowny trening nie zastąpi brakującej zmienności.

## 7. E1 — audyt bez treningu ML

### E1.1. Kontrakt danych i cechy elektryczne

1. Użyć jawnego wejścia audit_v3 powyżej; nie wybierać pierwszego pliku z glob.
   Porównać zakres i wybrane sygnały z `dataset_clean.parquet` i v1; ustalić,
   czy wcześniejszy dropna nie usuwa określonych stanów. Nie zmieniać źródeł.
2. Zapisać schemat tagów, jednostki, braki, rozkłady, najczęstsze wartości,
   odsetek zmian i długości stałych odcinków. Rozróżnić kwantyzację od
   potwierdzonego limitu regulatora. Zbadać różnice kolejnych unikalnych U/I.
3. Użyć funkcji czasu z `src/time_analysis.py`. Każda luka i nieprawidłowy pomiar
   analizowanego sygnału zrywa jego ciągłość. Nie interpolować U/I, statusów
   ani targetu. NaN w jednym pomocniczym tagu nie musi usuwać wszystkich pól.
4. R_app liczyć wyłącznie dla skończonych `U > 0`, `I > 0` i znanego załączenia.
   Flagi: brak, off, nieprawidłowy znak, niski prąd. Próg niski = 10 mA,
   analizy czułości 1 i 30 mA. Dla I poniżej wybranego progu R_app = NaN
   z flagą low_current; to reguły numeryczne audytu, nie granice sprzętu.
5. P_UI jest kontrolą algebraiczną. Sprawdzić jednostki i zaokrąglenia,
   zgodność tagów mocy, prądów/napięć pierwotnych oraz wtórnych. Brak pomiaru
   mocy czynnej sieci oznaczyć jawnie; nie liczyć sprawności z samych U*I
   pierwotnych bez informacji o współczynniku mocy i sposobie rejestracji.

### E1.2. Cykle i kontekst procesu

- Zidentyfikować 0→1 dla wszystkich sześciu tagów, z poprzednią próbką dokładnie
  10 s wcześniej. Czas od startu jest unknown przed pierwszym startem w segmencie;
  znany brak startu w ostatnim oknie wymaga obserwacji całego tego okna.
- Dla każdego tagu profile [−5,+15] min; baza to mediana punktowych wartości
  w [−5,−1] min, wyniki w [0,5), [5,10), [10,15). Dla rysunku zachować prawy
  punkt końcowy. Różnica tej konwencji od rozpoznania z sekcji 4 jest zamierzona.
- Oceniać U, I, R_app, P oraz pył. Najpierw zmiana w obrębie zdarzenia, dopiero
  potem mediana zmian. Oddzielnie pokazać profile median i agregaty próbek.
- Raportować wszystkie starty, okna pełne, braki, liczbę innych startów i czas
  aktywności innych strzepywaczy. Nie odrzucać całej próby przez warunek „zero
  innych zdarzeń”. Analiza izolowana może zakończyć się n=0 i to jest wynik.
- Zapisać profile względem dni i faz cyklu. Korelacje wartości i różnic 60/180 s
  liczyć wewnątrz ciągłych segmentów; dodatni lag to `corr(x(t), y(t+lag))`.
  Krzywe lagów w zakresie ±5 min są opisowe; nie wybierać z nich „opóźnienia
  fizycznego” ani wyłącznie najlepszego współczynnika.
- Podstawowy kontekst gazowy: moc generatora, przepływ spalin, średnia i różnica
  temperatur L/P, wilgotność, O2 przed OPP L/P, statusy palników. Rozszerzenie:
  powietrze, ciśnienia, SO2/NOx/CO/O2 BC1. Nie przypisywać znaku wpływu z góry.
- Sprawdzić, czy związki są widoczne w co najmniej trzech dniach i po
  uwzględnieniu cyklu. Pokazać rozkład współczynników po dniach, nie tylko
  współczynnik dla 210 tys. autokorelowanych próbek.

Rozpoznawczo użyć warstw napięcia o szerokości 2 kV i faz krytycznego cyklu
0–5, 5–15, >15 min; osobno pokazać aktywność pozostałych strzepywaczy.
Warstwa z mniej niż trzema dniami nie daje oceny powtarzalności. Zależności
w takich warstwach nadal są opisowe, nie są estymacją parametrów materiału.
Dla median zmian zdarzeń zastosować bootstrap całych dni (1000 powtórzeń,
seed=42) oraz sprawdzić wynik po pominięciu każdego dnia. Nie wybierać do
raportu tylko istotnych statystycznie kombinacji tagów.

### E1.3. Czy są warunki do porównań energetycznych?

Jednostka porównania: niepokrywające się bloki 10 min w pełnym segmencie 10 s.
60 lewych próbek i prawy punkt końcowy są potrzebne do energii. Blok zaczyna
się na pełnej wielokrotności 10 min; nie składać bloków przez lukę.

Na wspólnych ważnych przedziałach liczyć energię tagów mocy prostokątnie oraz
średnią moc `E / czas`. Podstawowe wyniki pyłu: średnia, P95, maksimum i czas
powyżej progów analitycznych 20/40 mg/Nm³. Progi nie są limitami instalacji.
Równolegle zachować pełną emisję i stratum poza ±15 min od krytycznego startu.
Nie wybierać do porównań wyłącznie bloków z niskim przyszłym pyłem.

Najpierw zwykła mapa zakresów; następnie porównania w kolejnych poziomach:

1. Moc generatora i przepływ spalin.
2. Dodatkowo T, wilgotność i O2 przed OPP.
3. Dodatkowo fazy/aktywność wszystkich sześciu strzepywaczy i statusy palników.

Porównywać bloki na różnych dniach, bez wspólnych próbek. Szukać maksymalnie
20 najbliższych kandydatów na blok, ze skalowaniem z okresu referencyjnego
przed 2025-07-12; nie liczyć macierzy odległości wszystkich próbek 10 s.
Sztywne tolerancje rozpoznawcze: generator ±2% względem wartości referencyjnej,
przepływ ±5%, średnia T ±2°C, różnica T L–P ±2°C, wilgotność ±0,2 punktu proc.,
każdy O2 przed OPP ±0,5 punktu proc. Statusy palników muszą być identyczne.
W trzecim poziomie: różnica czasu aktywności każdego strzepywacza ≤60 s/blok
i jednakowy koszyk czasu od ostatniego startu na początku bloku:
0–1, 1–3, 3–5, 5–15, >15 min, unknown. Unknown nie jest zwykłym koszykiem
„brak zdarzenia”; takie pary wyłączyć z potwierdzonego pokrycia poziomu 3.

Domyślny próg rozróżnienia mocy to jednocześnie ≥2 kW i ≥5% średniej mocy pary.
To filtr rozpoznawczy, nie obietnica ekonomiczna ani próg dokładności pomiaru.
Pokazać czułość 1/2/3 kW oraz tolerancji 0,5×/1×/2×, bez wybierania najkorzystniejszej.
Tworzyć pary bez ponownego użycia bloku, deterministycznie według odległości
i czasu. Raportować także liczbę kandydatów przed takim ograniczeniem.

Moc jest tu obserwowanym poziomem pracy, nie zadaną interwencją. Nie dopasowywać
par po bieżącym pyle ani U/I, jeśli porównujemy P: wynik i wielkości algebraicznie
związane z mocą mogłyby pozornie tworzyć lub usuwać efekt. Analiza pojedynczego
pola musi dodatkowo uwzględnić moce pozostałych pól; brak niezależnych zmian
oznacza brak możliwości przypisania efektu danej strefie.

Raport: udział godzin mających odpowiedniki, liczba unikalnych bloków/par/dni,
różnice kontekstu przed/po dopasowaniu, rozkład ΔP i różnic pyłu oraz wkłady
poszczególnych dni. Podawać standaryzowane różnice cech, ale nie nazywać dobrego
balansu dowodem braku ukrytych czynników.

Dla porównań par wykonać kontrolę po usunięciu każdego dnia, usuwając wszystkie
pary, których którykolwiek blok pochodzi z tego dnia. Nie traktować par
powiązanych wspólnymi dniami jako niezależnych obserwacji do prostego testu t.
W E1 wystarczą rozkłady i ta ocena stabilności; nie ogłaszać równoważności emisji.

Robocza bramka do dalszych **obserwacyjnych** porównań: ≥30 unikalnych par,
każda strona par reprezentowana przez ≥3 dni, żaden dzień nie odpowiada za
>50% bloków, pokrycie ≥10% kwalifikujących się godzin i bezwzględne
standaryzowane różnice kluczowego kontekstu ≤0,1. Dla cechy stałej sprawdzić
równość, zamiast dzielić przez zero. To jawne reguły przesiewowe projektu,
a nie obliczenie mocy statystycznej lub uniwersalny standard. Wynik n=0
przy rozsądnych tolerancjach kończy tę ścieżkę dla obecnych danych.

Brak różnicy statystycznej pyłu nie dowodzi równoważności. Do stwierdzenia
zachowania emisji potrzebny jest uzgodniony margines pogorszenia i odpowiedni
przedział ufności, a do oszczędności wskutek zmiany sterowania — H4.

## 8. E2 — mały test wartości danych procesowych, dopiero po E1

E2 służy ocenie modelu monitorującego stan, a nie optymalizacji nastaw. Można
go rozważyć mimo braku pokrycia energetycznego, jeśli E1 wykazuje powtarzalne
zmiany elektryczne niewyjaśnione samą fazą cyklu.

Pierwszy target: **bieżący prąd wtórny I danego pola przy obserwowanym U**.
Kolejno trzy pola, bez strojenia setek konfiguracji. Residuum `I − I_hat`
nazywać odstępstwem od oczekiwanej pracy w archiwum, nigdy automatycznie awarią,
back-coroną, marnowaniem energii ani pomiarem rho.

Porównania na identycznych znacznikach, raz na minutę:

- B0: mediana prądu z treningu oraz prosta regresja Ridge z U, U² i cyklem;
- B1: mały model drzewiasty z U danego pola i historią sześciu strzepywaczy;
- B2: ten sam model + podstawowy kontekst gazowy z E1;
- B3: B2 + SO2/NOx/CO/O2 BC1, powietrze i ciśnienia — tylko jeśli B2 przejdzie bramkę.

Stała propozycja: `HistGradientBoostingRegressor`, squared_error, max_iter=150,
max_leaf_nodes=15, min_samples_leaf=50, learning_rate=0.05,
l2_regularization=1, early_stopping=False, random_state=42.
Nie korzystać z losowej walidacji wewnętrznej do early stopping. Ridge:
StandardScaler dopasowany na train, alpha=1, U² wyliczane przed skalowaniem.

Wykluczone wejścia: bieżące I targetowego pola, jego R_app, G_app, P, prąd
pierwotny, sumy/różnice mocy pozwalające je odtworzyć oraz aktualny pył.
Pozostałe pola nie wchodzą do podstawowego modelu, aby nie zastąpiły badanego
wkładu procesu wspólną reakcją elektryczną. Osobny test pomocniczy dodaje
historię I sprzed 1 i 5 min do B1 oraz B2 i sprawdza, czy proces nadal wnosi
informację ponad pamięć pracy zasilacza. Przewagę B2 bez historii oceniać
oddzielnie od tej trudniejszej próby.

Kontekst: wartość dostępna teraz oraz średnia i zmiana z ostatnich 5 min;
bez przyszłych okien. Główne scenariusze dostępności procesu 0 i 120 s,
z osobnym oznaczeniem pomiarów gazowych o niepotwierdzonej filtracji.
To model retrospektywny przy założonej dostępności. Nie przesuwać sygnałów
o najlepszy lag dobrany na zbiorze oceny.

D1, D2, D3 jak w `src/forecast_validation.py`, nauka wyłącznie na wcześniejszych
okresach. Cały dotychczasowy miesiąc, włącznie z legacy, jest już oglądanym
zbiorem rozwojowym. Nie tworzyć z niego „nowego niezależnego testu”.
Ponieważ celem jest I(t), nie ma przyszłej etykiety; wspólna historia sprzed
granicy jest dozwolona przy odtwarzaniu online. Profile zdarzeń i bloki użyte
do oceny nie mogą przecinać granic foldów. Wszystkie transformacje, tolerancje
wyuczone i granice zakresu wsparcia ustalać na train.

Metryki: MAE w mA, RMSE, bias, błąd po dniu/polu/fazie cyklu oraz różnica MAE
B2–B1 na tych samych originach. Osobno poza krytycznym oknem rappingu i przy
odmiennym kontekście gazowym. Nie porównywać MAE wariantów na różnych brakach.
Raportować także procent originów, dla których model odmawia interpretacji
z powodu braku podobnego kontekstu w treningu.

Niepewność: sparowany bootstrap całych dni, 1000 powtórzeń, seed=42;
kontrola leave-one-day-out i przy grupowaniu sąsiednich dwóch dni. Jednostką
niezależności nie jest próbka co 10 s. Krótkie foldy dają słabą precyzję;
przedziały nie uwzględniają wszystkich błędów systematycznych.

Bramka B2: dodatnia poprawa MAE względem B1 w ≥2/3 foldów, średnia poprawa
≥5% w analizie poza krytycznym rappingiem, brak jednego dnia tworzącego całą
poprawę i raport przedziału ufności. 5% jest progiem przesiewowym projektu,
nie obietnicą operacyjną. Jeżeli CI obejmuje brak poprawy, wynik pozostaje
niejednoznaczny. Zaliczenie nie potwierdza H3 ani H4. E2 bez użytecznego
odstępstwa lub niezależnej walidacji nie wystarczy jako gotowa diagnostyka.

## 9. Warstwa energetyczna i granica przyszłej interwencji

Jeśli istnieje pokrycie E1, możliwy jest raport różnic energii w podobnych
warunkach. Niska warunkowa wartość mocy jest **benchmarkiem obserwowanym**,
nie minimalną mocą wymaganą do odpylania. Ranking ma wskazywać materiał do
przeglądu, wraz z podobnymi okresami, emisją i niepewnością.

Mierniki dopuszczalne już teraz: kWh z trzech tagów na wspólnym pokryciu,
średnie kW, udziały pól, porównania energii w równych oknach.
`kWh / objętość spalin` dopiero po potwierdzeniu wspólnego toru, baz sucha/mokra,
normalizacji i jednostki przepływu. Stosować iloraz całek, nie średnią ilorazów.
Nie obliczać kg usuniętego pyłu ani kWh/kg usuniętego pyłu bez pomiaru wlotowego.
Nie mnożyć mg/Nm³ przez przepływ w m³/h o nieustalonej bazie.

Przywrócenie celu „rzeczywista poprawa energetyczna” wymaga następnie:

1. Znanej wielkości zadawanej i ograniczeń działającego regulatora.
2. Wiarygodnego rozdzielenia zmian działania od zmian procesu, najlepiej
   poprzez zaplanowane porównania dopuszczonych nastaw przy zachowanych zabezpieczeniach.
3. Nowego okresu walidacji, odpowiedniego czasu ustalenia oraz uwzględnienia
   historii osadu i rappingu; krótkie A/B może mieć efekty przeniesienia.
4. Potwierdzonej energii elektrycznej na właściwej granicy pomiaru, pełnej emisji
   obejmującej również rapping i marginesu dopuszczalnego pogorszenia ustalonego
   przed testem. Energia w jednym polu może tylko przenosić koszt do innego.

To osobny przyszły projekt. Obecny dokument nie ustala wartości nastaw.
Symulowanie obniżania napięcia w dotychczasowym modelu PH ani optymalizacja
SHAP nie jest ewaluacją alternatywnej polityki sterowania. Nie wykonywać RL,
dużej optymalizacji lub ekstrapolacji rocznej jako obejścia braku H4.

## 10. Informacje z instalacji: co byłoby najbardziej wartościowe

Użytkownik zakłada, że dodatkowych informacji może być niewiele. E1 ma działać
na dostępnych danych i raportować unknown zamiast wstrzymywać audyt.

| Priorytet | Informacja | Co odblokowuje | Jeśli niedostępna |
| --- | --- | --- | --- |
| 1 | Producent/model zasilacza, tryb i lista rejestrowanych nastaw/limitów | Odróżnienie reakcji regulatora od zmiany warunków pola | Opis obserwacyjny, bez nazw trybów |
| 1 | Granica pomiaru mocy, tor gazowy, opóźnienie/filtracja pyłomierza | Wiarygodna energia i kierunek opóźnień | Energia tagów i analiza czułości, bez fizycznej kalibracji |
| 2 | Kilka zmian nastaw z czasem i powodem lub kolejny okres pracy | Ocena niezależnej zmienności i zewnętrzna walidacja | Brak potwierdzenia oszczędności |
| 3 | Referencyjne U–I, właściwości pyłu, etykiety usterek | Rozpoznanie mechanizmów, prawdziwa diagnostyka | Odstępstwa statystyczne bez etykiety awarii/rho |

Brak informacji nie unieważnia już wykonanych badań. Ogranicza tytuł i siłę
wniosków. Proponowany roboczy temat: **„Ocena stanu elektrycznego i możliwości
poprawy energetycznej przemysłowego elektrofiltru na podstawie danych
eksploatacyjnych i procesowych”**. Słowo „poprawa” jako wykazany rezultat
wymaga przyszłej walidacji interwencji.

## 11. Następna decyzja

Najbliższy etap to wyłącznie E1 według handoff. Po nim krótki werdykt:

- **A:** jest powtarzalny sygnał procesu i pokrycie energetyczne — E2 oraz
  obserwacyjny benchmark jako kandydat do późniejszej weryfikacji;
- **B:** jest sygnał, brak pokrycia — tylko E2 monitorujący stan;
- **C:** sygnał znika po uwzględnieniu cyklu albo jest zbyt ubogi — zamknąć
  kierunek na obecnym zbiorze i wskazać konkretny brak danych.

Żaden z tych werdyktów sam nie oznacza oszczędności. Osiągnięciem E1 będzie
odtwarzalna odpowiedź, którą z tych ścieżek uzasadniają istniejące dane.
