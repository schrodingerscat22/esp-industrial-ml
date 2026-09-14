# H: protokół hybrydowego modelowania i granic uogólniania ESP

Wersja 1, 2026-09-14. **Zamrożony projekt przed dopasowaniem modeli H.**
Wstępne rozpoznanie danych jest opisane w
[hybrid_esp_feasibility.md](hybrid_esp_feasibility.md). Zmiany protokołu zapisywać
z datą, powodem i informacją, które wyniki były już znane. Jest to odrębny
kierunek H; nie redefiniuje F1–F3 ani nie unieważnia decyzji E1/E1.5.

## 1. Pytanie, hipotezy i wynik użytkowy

Pytanie: czy jawne ograniczenia inspirowane fizyką wychwytu i reemisji pyłu
poprawiają generalizację modelu ESP na obserwowane, lecz nieobecne w treningu
reżimy, oraz pozwalają wyznaczyć granicę między przewidywaniem a scenariuszem?

- H-G: hybryda ma mniejszy błąd w wyłączonych z treningu reżimach niż model ML
  o tych samych wejściach i porównywalnym nakładzie strojenia.
- H-D: do tej samej jakości potrzebuje mniejszej liczby dni treningowych.
- H-U: wskaźnik pokrycia i niepewności rozpoznaje obszary rosnącego błędu.
- H-S: wnioski scenariuszowe pozostają zgodne między rozsądnymi, nieodrzuconymi
  wariantami modelu i parametrów. Możliwy wynik: brak takiej zgodności.

Wynik: model warunkowego stężenia pyłu, mapa jego sprawdzonego zakresu,
granice identyfikacji i ewentualnie katalog scenariuszy do przyszłej weryfikacji.
Nie jest to identyfikacja regulatora ani dowód wpływu zmiany nastawy na emisję.

## 2. Dwa poziomy modelu, których nie wolno utożsamiać

### Poziom A — dostępny teraz

Zredukowany model stężenia z ograniczeniami inspirowanymi fizyką. Wartości
efektywne opisują archiwum; nie nazywamy ich rho, masą osadu, powierzchnią
ani sprawnościami pól. Ta wersja nie potrzebuje geometrii i pomiaru C_in.

### Poziom B — model bilansowy

Model szeregowych sekcji, gazu i magazynowania osadu. Na dziś: **wyłącznie
syntetyczny obiekt referencyjny**, w bezwymiarowych jednostkach lub z kompletną,
wyraźnie fikcyjną konfiguracją. Kalibracja na instalacji wymaga niezależnej
informacji o geometrii, bazach przepływu i dopływie pyłu albo wiarygodnych
ograniczeń tych wielkości. Brak komend regulatora nie blokuje samego bilansu,
lecz pozostaje problemem przy interpretacji zmian elektrycznych jako działań.

Model zastępczy ciężkiego symulatora ma uzasadnienie, gdy mierzalnie przyspiesza
obliczenia przy akceptowalnym błędzie. Prosty model z kilku równań można liczyć
bezpośrednio; nie dodawać sieci wyłącznie po to, by nazwać ją surrogatem.
Dokładność względem symulatora i względem rzeczywistego ESP to dwa osobne wyniki.

## 3. H0 — kontrakt danych i identyfikowalność

Źródło główne: `data/processed/audit_v3/df_model_clean_v1.parquet`.
Porównać selekcję z `data/processed/dataset_clean.parquet` bez nadpisywania
żadnego źródła. Pełną listę parametrów i ich status przechowywać jako:
`measured`, `metadata_only`, `assumed_synthetic`, `effective_fitted`, `unknown`.
Każdy parametr ma jednostkę, zakres stosowalności i źródło. Nie zamieniać
`unknown` na „typową wartość” bez jawnego scenariusza.

Źródła cech:

- U/I/P i rapping: `FIELDS`, `RAPPING_TAGS` z `src/electrical_state.py`.
- Pył: `008A01345`.
- Proces podstawowy: obciążenie `008A00936`, przepływ `008A01353`, temperatury
  `008A00720/008A00728`, wilgotność `008A02118`, O₂ `008A00741/008A00742`,
  cztery statusy palników `008B01474/01479/01484/01489` z pełnym prefiksem 008B.
- CO/NOx/SO₂, pozostały O₂, powietrze i ciśnienia są rozszerzeniem H3,
  nie dodawać ich automatycznie do pilotażu.

Sprawdzić braki, znaki, kwantyzację, częstość zmian, stałe statusy, zależność
U/I/P i wspólną zmienność pól. Standaryzowany rząd macierzy cech i profile
funkcji celu są diagnostyką numeryczną; pełny rząd nie dowodzi identyfikacji
fizycznej. Źródła muszą zachować SHA-256 przed/po.

Obowiązkowe demonstracje syntetyczne: niejednoznaczność C_in–K oraz A–w;
powtórzyć odzyskiwanie parametrów z kilkoma startami przy znanym i nieznanym
wlocie. Parametr zmieniający się silnie bez zmiany predykcji nie może otrzymać
interpretacji fizycznej. Priory/ograniczenia mogą wybrać rozwiązanie, ale
trzeba wskazać, jaka część wyniku pochodzi z tych założeń.

Bramka G0: można zbudować wspólną próbę procesu/U/I/rappingu/pyłu i wyjaśnić
jednostki lub jawnie ograniczyć się do wskaźników względnych. Brak geometrii
blokuje kalibrację B, **nie** pilotaż A. Brak wymaganych pomiarów daje raport
odrzuceń, nie automatyczny zamiennik sygnału.

## 4. Czas, dostępność i cel modelowania

Główny target to **C_out(t)**, estymowane z obserwowanego procesu, U/I i
historii rappingu do t. Jest to retrospektywny model warunkowy, bez bieżącego
i historycznego pyłu w wejściach modeli głównego porównania. Nie nazywać go
prognozą ani odpowiedzią na interwencję. Odrębny pomocniczy baseline persistence
otrzymuje C_out(t−60 s); jego przewaga informacyjna musi być oznaczona.

Budować wszystkie cechy na siatce 10 s, następnie wybierać dokładne originy
pełnych minut. Nie agregować rappingu przed wykryciem 0→1, bo można zgubić
krótkie starty. Pył zachować w oryginalnej bazie mg/Nm³, bez odrzucania pików.

- Użyć `validate_time`, `segments`, `time_shift`, `complete_window`, `coverage`.
  `segments` rozdziela tylko luki znaczników: dodatkowo zrywać historię
  analizowanego sygnału na NaN/Inf i statusie nieznanym. Test ma to wymusić.
- Nie interpolować targetu, U/I i stanów rappingu. Wymagana historia jest
  kompletna do ostatniego punktu. Próbka za luką nie pamięta stanu osadu.
- Proces: wartości teraz, średnia i zmiana z poprzednich pięciu minut.
  U/I: wartości teraz; historia 60/300 s jest osobną ablacją H3.
- Rapping: stan bieżący oraz przyczynowe sploty obserwowanych startów sześciu
  tagów z trzema jądrami z sekcji 5. Po luce wymagać 15 min pełnej historii.
- Scenariusz podstawowy: dostępność pomiarów procesu bez dodatkowego opóźnienia.
  Obowiązkowa czułość H3: te same wejścia procesowe opóźnione o 120 s.
  Nie dobierać najlepszego laga na D1–D3. Znaczenie wyniku zależy od tych założeń.
- Brak sygnału na początku segmentu to brak predykcji, nie zerowy rapping.
- Liczyć osobno wiersze, daty z danymi, rzeczywisty czas pokrycia, segmenty,
  starty, originy oraz odrzucenia z każdej przyczyny i po wspólnej masce.

W eksperymencie scenariuszowym nie wolno zasilać modelu rzeczywistą przyszłą
trajektorią U/I i nazywać jej prognozą skutków alternatywnego sterowania.
Każdy taki sygnał jest albo zadanym warunkiem scenariusza, albo wynikiem osobnego,
zweryfikowanego modelu odpowiedzi elektrycznej. C_out(t) nie może aktualizować
stanu ukrytego przed oceną predykcji w tej samej chwili.

## 5. H1 — modele i minimalna fizyka

### 5.1. Szkielet bilansowy B dla testów syntetycznych

Dla pola j, strumieni masy F [kg/s] i masy osadu M [kg]:

```text
eta_j = 1 - exp(-K_j),       K_j = w_j * A_j / Q
F_j   = (1-eta_j) * F_(j-1) + R_j
dM_j/dt = eta_j * F_(j-1) - R_j - H_j
C_out = F_3 / Q             (tylko przy zgodnych bazach)
```

R_j to strumień reemisji z osadu, H_j to strumień do leja; wszystkie strumienie
są nieujemne. Zdarzenie usuwa tylko część dostępnego osadu, podzieloną między
gaz i lej. Numeryczny krok nie może usunąć więcej masy, niż jest dostępne.
Reemisja wcześniejszego pola przechodzi przez pola następne; dla ostatniego
nie dodawać fikcyjnego kolejnego wychwytu. To jawne założenie układu szeregowego
syntetycznego obiektu, nie potwierdzenie topologii wszystkich torów instalacji.

Model transportu i czujnika może zawierać przyczynowe opóźnienie i filtr
pierwszego rzędu z dodatnim czasem. Nie dopasowywać swobodnie równocześnie
opóźnienia transportu, rappingu i pyłomierza z jednego wyjścia. W syntetyce są
znane; na instalacji raportować efektywne opóźnienie i analizę czułości.

Szkielet bazuje na klasycznej relacji wychwytu; pomija m.in. rozkład rozmiaru
cząstek, przestrzenny przepływ i back-coronę. To założenia ograniczające model.
[EPA: wychwyt i ograniczenia modeli ESP](https://www.epa.gov/sites/default/files/2020-07/documents/cs6ch3.pdf).
Historia osadu i rapping są ważnymi dodatkowymi dynamikami;
[EPA: model reemisji i jego ograniczenia](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=9100R8RJ.TXT).

### 5.2. Rdzeń A możliwy bez geometrii i wlotu

Zdefiniować na dodatnich wartościach, z medianami **wyłącznie treningowymi**:

```text
u_j(t) = U_j(t) / median_train(U_j)
q(t)   = Q_tag(t) / median_train(Q_tag)
chi(t) = mean_j(u_j(t)^2) / q(t)
C_core(t) = C_unit * exp(beta0 + beta_z * z(t) - a*(chi(t)-1))
            + sum_(r,tau) b_(r,tau) * phi_(r,tau)(t)
```

C_unit=1 mg/Nm³ ustala jednostkę liczbową. z to standaryzowany proces podstawowy
(średnia i różnica T L/P, oba O₂, MW, przepływ, wilgotność, palniki, wyżej opisane
cechy pięciominutowe), bez U/I i bez pyłu. Stałe cechy usuwać na train.
Na początku stosować regresję liniową z, bez sieci i swobodnego C_in(t).

chi jest **względnym wskaźnikiem ekspozycji**, nie natężeniem pola ani zmierzoną
liczbą Deutscha. Potęga 2 i jednakowe wagi pól są zamrożonym założeniem pilotażu;
nie twierdzimy, że pola mają jednakową geometrię. Przepływ w tej formule jest
proxy z tagu. Nie daje czasu przebywania ani strumienia masy pyłu.

phi jest sumą jąder po wszystkich zaobserwowanych startach danego rappingu:
`k_tau(s)=(s/tau)*exp(1-s/tau)*v(s)` dla `0<=s<=900 s`, poza tym 0;
v=1 do 600 s, następnie v=(900−s)/300. Wygaszenie zapobiega sztucznemu skokowi
na końcu pamięci; 15 min jest wyborem modelowym, nie zmierzonym czasem zaniku.
tau = 30, 120, 300 s. Sumować nakładające się odpowiedzi, nie przypisywać całego
piku ostatniemu startowi. b>=0 ma jednostkę stężenia i jest efektywną amplitudą,
nie kilogramami osadu. Współliniowe rappingi mogą nie mieć rozdzielnych b.

Podstawowo a>=0. Monotoniczność odnosi się tylko do tego rdzenia przy stałym
procesie; back-corona, regulator i wspólne wymuszenia mogą unieważnić ją dla
całego obserwowanego układu. Nie wymuszać jej globalnie dla pyłu względem I/P.
Na tych danych także beta0 **nie** jest oszacowaniem stężenia wlotowego.

Dopasowanie: znormalizowana suma kwadratów reszt `log1p(C/C_unit)` plus
`0.01*sum(theta_penalized^2)`; intercept bez kary, amplitudy b skalowane przez
medianę treningowego pyłu wyłącznie dla kary numerycznej. SciPy least_squares,
max_nfev=200, trzy deterministyczne starty, jawne warunki a,b>=0. Zapisać
zbieżność, skończoność, parametry brzegowe i różnice między startami.
Brak zbieżności daje niezaliczony model, nie przedłużanie optymalizacji w pętli.

### 5.3. Wspólne porównanie

| Model | Rola |
| --- | --- |
| M0 | Ridge na procesie i rappingu, bez elektryki; baseline harmonogramu |
| M1 | ML: HistGradientBoosting na X wspólnym, bez rdzenia |
| M2 | Powyższy rdzeń A, bez korekty ML |
| M3 | Ten sam rdzeń + mała korekta ML; kandydat hybrydowy |
| P60 | Pomocnicze C_out(t−60 s); dostęp do historii pyłu oznaczony jawnie |

X wspólne = z, U/I trzech pól, chi, sześć stanów rappingu i 18 phi.
M1 oraz korekta M3 dostają identyczne X, w tym ten sam wskaźnik chi; to chroni
przed przypisaniem przewagi samemu dodaniu innej cechy. Nie podawać P ani U/I
jako dodatkowych „niezależnych pomiarów”. Nie odtwarzać mocy z bieżącego U/I
jako celu świadczącego o jakości fizyki.

M1 i korekta M3: max_iter=150, max_leaf_nodes=15, min_samples_leaf=50,
learning_rate=0.05, l2_regularization=1, early_stopping=False, seed=42.
M0: StandardScaler+Ridge(alpha=10). M0/M1 uczą log1p(C/C_unit); wyniki oceniać
po odwróceniu transformacji. Raportować odsetek obciętych ujemnych predykcji.

Korekta M3 uczy reszty `log1p(C/C_unit)-log1p(C_core/C_unit)` wyznaczone
**poza próbą dopasowania rdzenia**, na kolejnych dwudniowych blokach train,
po początkowych co najmniej trzech datach nauki. Rdzeń dla bloku zna tylko
wcześniejsze dane. Odrzucić bloki bez pokrycia; nie robić losowego cross-fittingu.
Końcowy rdzeń dopasować na całej części fit; raportować różnicę jakości między
rdzeniem końcowym i rdzeniami tworzącymi reszty.

Predykcja M3:
`C_unit * max(0, expm1(log1p(C_core/C_unit) + w(x)*delta_ML(x)))`.
w=1 w obszarze wsparcia treningowego i maleje do 0 wraz z odległością (sekcja 7).
Wyzerowanie korekty poza wsparciem **nie** potwierdza poprawności rdzenia.
Predykcję tam oznaczyć jako scenariusz zależny od założeń.

Nie dublować roli fizyki: bez równoczesnego uczenia swobodnych C_in, w, A,
rho, stanów osadu i korekty. Zasada rozdzielenia kalibracji i błędu modelu:
[Kennedy i O’Hagan](https://doi.org/10.1111/1467-9868.00294).

## 6. H2/H3 — walidacja w czasie i między reżimami

Użyć granic `DEVELOPMENT_FOLDS` z `src/forecast_validation.py`: D1 12–17 lipca,
D2 17–22, D3 22–27 lipca 2025. Nauka tylko przed początkiem oceny. Nie używać
legacy do wyboru projektu. Cały miesiąc był już oglądany; wszystkie te wyniki
nazywać rozwojowymi. Nowy podział nie tworzy niezależnego testu publikacyjnego.

W każdym outer train ostatnie dwie **daty z danymi** przeznaczyć na kalibrację
przedziałów, wcześniejsze na fit i jego chronologiczne reszty. Kalibracja nie
wybiera modelu, hiperparametrów ani zakresu wsparcia. Gdy po podziale brak
co najmniej trzech dat na fit, oznaczyć fold jako niewystarczający.
Pary origin–target są wspólne dla M0–M3; osobno raportować P60 z jego pokryciem.

H2: jedna konfiguracja na D1, bez strojenia. To próba uruchomienia i skali,
nie ostateczna decyzja na podstawie korzystnego lub niekorzystnego jednego folda.
H3: ten sam protokół na D1–D3 oraz trzy predefiniowane wyłączenia reżimów:

1. obciążenie >P80;
2. przepływ >P80;
3. obciążenie <P20.

Granice pochodzą z outer fit przed wyłączeniem, bez użycia pyłu ani błędów.
Następnie usunąć te reżimy z fit i kalibracji; skalowanie, rdzeń, reszty i ML
uczyć od nowa na zredukowanym fit. Osobno oceniać przyszłe originy należące do
wyłączonego reżimu oraz resztę przyszłej próby. Nie dopuszczać historii
przechodzącej przez wyłączony epizod w **treningu**: bufor co najmniej 1020 s
(900 s jądra + 120 s czułości dostępności). Okna zdarzeń muszą w całości
należeć do odpowiedniej roli zbioru. Historia obserwowana online przed
originem oceny jest dopuszczalna; nigdy przyszły target.

Sprawdzić nakładanie wyłączeń: obciążenie i przepływ mogą reprezentować ten
sam reżim. Nie przedstawiać skorelowanych prób jako niezależnych replikacji.
Minimum do interpretacji danego testu: 300 originów minutowych na co najmniej
trzech datach. Próg niezaliczony => „niewystarczające pokrycie”; nie zmieniać
percentyla do uzyskania korzystnego wyniku.

To eksperyment z luką **w danych treningowych**, oceniany na realnych danych
z przyszłego odcinka. Nie dowodzi działania poza całym dostępnym archiwum.
Krzywa uczenia H-D: ostatnie 4/8/wszystkie dostępne daty fit, ten sam zbiór
kalibracji i oceny; wariant pomijać, jeśli nie pozwala na cross-fitting.

## 7. Pokrycie i niepewność

Wspólny model wsparcia dla porównywanych wariantów: z poziomów procesu i U/I
oraz faz sześciu rappingów, bez targetu i jego historii. Nie utożsamiać
prostokąta min–max z pokryciem kombinacji parametrów.

Praktyczny pilot: skalowanie medianą/IQR fit (cechy stałe wymagają zgodności,
nie dzielenia przez zero), maksymalnie 20 tys. deterministycznie próbkowanych
referencyjnych originów, k=20 sąsiadów. Dla odległości kalibrujących zakres
fit wykluczyć sąsiadów z tej samej daty; próg d95 jest P95 odległości do
20. sąsiada. Kandydat musi mieć sąsiadów z co najmniej trzech dat.
Gdy nie można spełnić tej reguły, wsparcie jest nieznane. Kategorie/stany
niewidziane na fit i naruszenie dodatniości U/Q => poza zakresem.

w(x)=clip(2-d(x)/d95,0,1), z osobną obsługą d95=0 i braku wsparcia.
`supported`: d<=d95 i spełnione wymagania sąsiadów; `marginal`: d95<d<2*d95;
`outside`: d>=2*d95 lub nowa kategoria, brak trzech dat albo naruszenie zakresu
zmiennej stałej. Stan unknown/outside ma w=0 i jawny powód odmowy interpretacji.
Nazwa supported opisuje wsparcie cech, nie sama w sobie walidację fizyki. Zwykłe
predykcje testowe można policzyć również poza zakresem w celu oceny błędu,
ale nie ukrywać tego oznaczenia ani nie wykluczać ich z raportu pełnej próby.

Niepewność zawiera różne rzeczy:

- Błąd przewidywania w obserwowanych warunkach: nominalny przedział 90% z
  reszt części kalibracyjnej; sprawdzić faktyczne pokrycie, szerokość i interval
  score na przyszłych danych. Osobno podawać wyniki po dniach i reżimach.
- Niepewność porównań metryk: sparowany bootstrap całych dat, 1000 replik,
  seed=42, oraz analiza bloków dwóch kolejnych dni i leave-one-day-out.
  Dni bez danych nie sąsiednie na zegarze nie tworzą ciągłego bloku.
- Niepewność parametrów/struktury: kilka startów, profil a oraz ablacjami
  opisane rodziny modeli; w H4 propagować wszystkie nieodrzucone warianty.
- Nieznana kalibracja czujnika i błędna fizyka: osobne scenariusze, nie
  ukrywać ich w wąskim przedziale regresji.

Kalibracja w dotychczasowym reżimie nie zapewnia nominalnego pokrycia poza nim.
Mała rozbieżność podobnych modeli też nie dowodzi małego błędu systematycznego.
Nie raportować częstotliwości przekroczeń prawnego limitu ani bezpieczeństwa
bez kontraktu pomiaru i odpowiedniej walidacji.

## 8. Metryki, ablacje i bramki decyzyjne

Główna metryka: średnia z dziennych MAE w mg/Nm³ (równa waga dat).
Dodatkowo łączne MAE/RMSE/bias/R², P90/P95 błędu, liczba originów i dat,
czas pokrycia, błąd po obciążeniu/przepływie i rappingu, krzywa błąd–odmowa.
R² nie porównywać między różnymi podzbiorami jako miary przyrostu jakości.

Dla kompletnych okien startu rappingu [−5,+15] min porównać zmierzone i
modelowane maksimum, czas piku i całkę stężenia ponad własną bazą [−5,−1] min.
Całka ma jednostkę mg·min/Nm³, **nie masę ani energię**. Grupować nakładające
się okna w epizody przy niepewności; jeżeli tworzą jeden wielki epizod,
stosować bloki dni i nie deklarować wielu niezależnych zdarzeń.

Obowiązkowe ablacje H3:

- M3 vs M1 (taka sama informacja wejściowa) i M2 vs M3;
- rdzeń bez a oraz wariant bez ograniczenia znaku a;
- chi z potęgą 1 zamiast 2, pozostałe reguły identyczne;
- wszystkie sześć rappingów vs tylko krytyczny vs bez rappingu;
- proces + elektryka vs same cykle;
- opóźnienie procesu 0 vs 120 s;
- podstawowy model vs ten sam z historią U/I (osobne pytanie predykcyjne).

Kontrola błędnej fizyki: model z nieprawidłowym bilansem lub znakiem na
syntetyce powinien zostać odrzucony przez testy/ocenę. Na danych instalacji
lepszy wynik swobodnego znaku może ujawniać confounding lub nietrafną
strukturę, nie dowodzi odwrócenia prawa wychwytu. Test wpływu fizyki nie może
polegać wyłącznie na porównaniu ze słabo przygotowanym baseline.

G1: syntetyczne testy czasu, bilansu, ograniczeń i braku przecieku przechodzą;
na błędnej fizyce lub nieidentyfikowalnym przypadku procedura nie tworzy
fałszywego potwierdzenia parametrów. To dopuszcza dopiero ocenę na instalacji.

G2 po H3 — przesiewowa przesłanka przewagi H-G:

- mediana względnej poprawy dziennego MAE M3 względem M1 >=5% w kwalifikujących
  się testach wyłączonych reżimów i dodatni znak w co najmniej dwóch foldach;
- dolna granica 95% blokowego CI łącznej sparowanej poprawy >0;
- brak pogorszenia pełnego MAE i P95 błędu o >5% względem M1;
- wynik nie zależy wyłącznie od jednego dnia lub jednej wersji założeń;
- jawny raport przedziałów i odmów; brak pozornej przewagi przez usunięcie
  trudniejszych originów tylko dla hybrydy.

5% to ustalony próg przesiewowy projektu, nie spodziewany efekt ani wartość
operacyjna. Nakładające się wyniki tych samych timestampów między ablacjami
nie są nowymi próbkami do bootstrapu; każdą parę porównywać na oryginalnych
datach, a agregat między eksperymentami raportować bez sztucznego zwiększania n.
CI obejmujące zero => wynik niejednoznaczny. Brak dostatecznych reżimów =>
brak testu H-G. Korzystny D1 sam nie zalicza G2.

Jeżeli hybryda nie pokona ML, zbadać wynik H-U i identyfikowalność, ale nie
ogłaszać sukcesu uogólniania. Po zamrożonych ablacjach zakończyć ten wariant;
nie uruchamiać kolejnych sieci w poszukiwaniu korzystnej liczby.

## 9. H4 — scenariusze, energia i wartość informacji

H4 jest osobnym etapem po raporcie H3; negatywne H3 może uzasadnić wyłącznie
syntetyczne badanie ograniczeń, nie scenariusze instalacyjnej optymalizacji.

Scenariusze dzielić na `observed_tested`, `historical_but_withheld`,
`simulation_only`, `unresolved`. Zapisać źródło parametrów, wejścia zadane,
stany początkowe, czas rozgrzewania modelu i zależność wyniku od założeń.
Nie losować niezależnie U/I/P ani wszystkich stanów procesu z prostokątnych
zakresów. Scenariusz musi respektować zależności elektryczne i bilansowe;
bez charakterystyki I(U,stan) zmiana U nie określa mocy.

Energia z U[kV], I[mA]: `sum_j U_j*I_j/1000` kW jest przybliżeniem po stronie
zarejestrowanej elektryki. Uśrednianie i zasilanie impulsowe mogą łamać
utożsamienie iloczynu średnich ze średnią mocą. Całkować na rzeczywistych
ciągłych przedziałach; P-tag rozpatrywać osobno. Nie zamieniać tego w energię
sieciową, sprawność zasilacza ani roczną oszczędność bez dalszych danych.

Raportować zakres wyników energii i pyłu między nieodrzuconymi modelami.
„Wszystkie rozpatrzone modele przewidują spadek” oznacza odporność względem
tego zbioru założeń, nie gwarancję instalacyjną. Jeśli znak się zmienia,
wynik brzmi „nierozstrzygnięte”. Nie wybierać optymalnej nastawy z modelu A.

W syntetyce porównać redukcję niepewności po ujawnieniu kolejno C_in,
geometrii, właściwości pyłu i udokumentowanego wymuszenia. To może dać
użyteczny ranking wartości informacji nawet jeśli nie uzyskamy nowych pomiarów.
Nie deklarować, że jest to ilościowa wycena informacji dla rzeczywistego ESP.

## 10. Wynik raportu i zakres prawdziwego sukcesu

Raport musi osobno podać: wyniki sprawdzone na historii, wyniki syntetyczne,
hipotezy mechanizmów, parametry zależne od założeń i wyniki nierozstrzygnięte.
Nie używać określeń „zmierzona rho”, „zidentyfikowany PID”, „bezpieczny obszar
nastaw” ani „potwierdzona oszczędność” dla rezultatów tego protokołu.

Potwierdzenie H-G/H-D dałoby empiryczny argument na rzecz ograniczeń fizycznych
przy ograniczonych danych. H-U daje sprawdzony zakres zastosowania. H-S może
pokazać, czy w ogóle warto inwestować w model scenariuszowy. Negatywny wynik
też zamyka konkretne pytanie; nie jest powodem do nieograniczonego strojenia.
