# H: wykonalność hybrydowego modelu ESP

Stan: 2026-09-14. Studium wykonalności i propozycja badania, **bez treningu
nowego modelu ESP**. Punkt wyjścia: `1adcd47`, gałąź
`codex/methodology-audit`. Protokół: [hybrid_esp_methodology.md](hybrid_esp_methodology.md).
Instrukcja wdrożenia: [hybrid_esp_handoff.md](hybrid_esp_handoff.md).

## 1. Werdykt

**Warunkowe GO dla małego badania modelu z ograniczeniami fizycznymi i granic
jego uogólniania. NO-GO dla przedstawiania go obecnie jako skalibrowanego
cyfrowego bliźniaka instalacji lub potwierdzonego optymalizatora energii.**

Pomysł wykracza poza samą diagnostykę. Można badać, czy fizyczna struktura
modelu zmniejsza zapotrzebowanie na dane, poprawia przewidywanie w słabiej
reprezentowanych reżimach i pozwala uczciwie odmówić odpowiedzi tam, gdzie
brakuje podstaw. Jest też miejsce na symulacyjne badanie wariantów procesu
i ocenę, jakie pomiary najbardziej zmniejszyłyby niepewność. Te rezultaty
nie wymagają rozpoznania PID ani nowego tagu komendy regulatora.

Trzeba odróżnić trzy zakresy:

1. **Obserwowany:** rzeczywiste kombinacje warunków w historii. Nie powiększy się
   od wygenerowania danych syntetycznych.
2. **Zweryfikowany predykcyjnie:** reżimy rzeczywiście zmierzone, ale usunięte
   z treningu, na których sprawdzono model. Ten zakres może okazać się szerszy
   dla hybrydy niż dla modelu czysto danych.
3. **Symulowany:** warunki poza całym archiwum. Można obliczyć scenariusze pod
   jawnymi założeniami fizycznymi; nie ma tam oceny błędu względem instalacji.

W szczególności dopasowanie obserwowanego U/I nie oznacza znajomości odpowiedzi
na zadaną zmianę napięcia. Fizyczny model może dostarczyć takich przewidywań
warunkowo, ale wtedy ich uzasadnienie pochodzi z niezależnie wiarygodnej fizyki
i parametrów, a nie z samego dopasowania historii zamkniętej pętli.

## 2. Co sprawdzono lokalnie

Wykonano `scripts/assess_hybrid_esp_feasibility.py`. Raport agregatów pozostaje
w ignorowanym `data/processed/hybrid_esp_feasibility_20260914/preflight.json`.
Skrypt odczytuje wejście i oblicza deskryptywne statystyki oraz syntetyczny
przykład niejednoznaczności parametrów. Nie tworzy predykcji przemysłowych.

- Wejście: `data/processed/audit_v3/df_model_clean_v1.parquet`.
- 210 642 wiersze, 76 kolumn; 32 dni rozpiętości, **27 dat z obserwacjami**,
  24,37882 dnia ciągłego pokrycia, osiem luk, 76,18% pokrycia rozpiętości.
- Wszystkie tagi wymagane przez rozpoznanie elektryczne i procesowe są obecne.
  To nie potwierdza kompletności pomiarów fizycznych ani pochodzenia czyszczenia.
- Starty sześciu rappingów: 1 949 / 5 542 / 811 / 3 098 / 423 / 1 646, kolejno
  kolektor/ulotowe dla pól 1, 2, 3. Start wymaga 0→1 w odstępie dokładnie 10 s.
- SHA-256 przed i po identyczny:
  `686910605846534322f45d196d602bcf98fe256a93fda94edc429c081e629260`.
- `.venv`: Python 3.12.14, NumPy 2.3.5, pandas 3.0.1, SciPy 1.18.1,
  scikit-learn 1.9.0. To wersje faktycznie zaimportowane; różnią się od
  historycznego `requirements.txt`. Nie aktualizowano pakietów.
- 41 testów repozytorium OK; `pip check` OK. To kontrola istniejącego kodu,
  nie walidacja nieistniejącego jeszcze modelu hybrydowego.
- Podczas rozpoznania: ok. 13,09 GiB wolnego dysku, 5,59 GiB dostępnego RAM;
  RSS procesu po obliczeniach ok. 0,41 GiB, **nie pomiar maksimum**.

Zakresy P5–P95 z tego samego wejścia:

| Sygnał | Zakres | Konsekwencja |
| --- | --- | --- |
| Moc generatora | 30,1–36,0 MW | Ograniczony zakres zwykłego obciążenia |
| Tag przepływu spalin | 139–159 tys. m³/h | Baza objętości i tor niepotwierdzone |
| Temperatury za OPP L/P | 121–133 / 121–135°C | Przydatny kontekst, nie potwierdzona temperatura wewnątrz ESP |
| Wilgotność spalin | 4,4–5,1% | Przydatna, lecz wąski zakres |
| U pól 1/2/3 | 46–50 / 40–42 / 37–42 kV | Mała niezależna zmienność elektryczna jest ryzykiem |
| Trzy najczęstsze wartości I pól 2/3 | ok. 95% / 93% próbek | Kwantyzacja lub regulacja ograniczają kalibrację charakterystyk |

W [E1](electrical_energy_validation.md) nie było nominalnie dopasowanych par
energetycznych; po rozluźnieniu tolerancji znaleziono osiem par i 0,46% godzin.
To dowód problemu porównywalności przy przyjętym kryterium, nie matematyczny
dowód niemożności jakiejkolwiek identyfikacji. Model fizyczny nie usuwa tego
problemu automatycznie.

W [audycie odpowiedzi](controller_response_validation.md) wykluczenie wszystkich
rappingów pozostawiło zero zdarzeń. Inspekcja kodu precyzuje: „aktywne” oznaczało
**0–15 min od startu**, a nie tylko status pracującego silnika. Nie wolno z tego
wywnioskować, że każdy pik występuje podczas faktycznej aktywności silnika lub
że krótsza, uzasadniona maska też musi dać zero. H analizuje wspólnie sześć
historii startów i nie uzależnia całego badania od znalezienia izolowanych pików.

## 3. Dostępność informacji fizycznej

| Potrzeba modelu | Co mamy | Dozwolone użycie / brak |
| --- | --- | --- |
| Elektryka trzech zespołów | U, I, P, rzadkie przeskoki, załączenie | Zmierzone warunki/odpowiedź; brak nastaw i charakterystyk poza zakresem |
| Transport gazu | `008A01353`, temperatury L/P, wilgotność, ciśnienia | Kontekst i bezwymiarowe wskaźniki; nie składać bilansu masy bez zgodności baz i torów |
| Obciążenie i spalanie | MW generatora, O₂, powietrze, CO/NOx/SO₂, palniki | Wskaźniki wymuszeń; nie pomiar strumienia, składu ani granulometrii popiołu |
| Zdarzenia mechaniczne | Sześć potwierdzeń rappingu | Historia startów i pracy; brak siły uderzenia i masy oderwanego osadu |
| Wynik odpylania | Jeden pyłomierz `008A01345`, mg/Nm³ | Wynik obserwowanego toru; nie sprawność każdego pola |
| Geometria | Brak potwierdzonego A, rozstawów, długości i podziału przepływu | Nie obliczymy E=U/d ani gęstości prądu z wymyślonego d/A |
| Dopływ pyłu | Brak C_in i rozkładu rozmiaru cząstek | Nie wyznaczymy rzeczywistej sprawności ani kg usuniętego pyłu |
| Właściwości osadu | Brak rho, składu, grubości i masy | Możliwy parametr efektywny, bez nazywania go zmierzoną rezystywnością |
| Tor pomiarowy | Brak potwierdzonej filtracji, opóźnienia i normalizacji | Analiza czułości; dynamika modelu może obejmować dynamikę przyrządu |
| Granica energetyczna | P niemal równe U×I/1000 | Energia z trzech tagów; nie potwierdzona energia całej instalacji z sieci |

Pełne mapowanie: sekcja 5 [electrical_energy_methodology.md](electrical_energy_methodology.md).
Nie zakładamy, że użytkownik dostarczy brakujące tagi. Projekt ma ścieżkę
działającą bez nich; bogatszy model fizyczny pozostaje warunkowym rozszerzeniem.

## 4. Najważniejsza granica identyfikacji

W uproszczeniu bez reemisji `C_out = C_in * exp(-K)`, gdzie
`K = sum(w_j * A_j / Q)`. To szkielet, którego zakres stosowalności trzeba
ocenić; klasyczne równania i ograniczenia opisuje
[EPA, rozdział o ESP](https://www.epa.gov/sites/default/files/2020-07/documents/cs6ch3.pdf).

**Własny argument identyfikacyjny:** dla dowolnego dodatniego `a` zamiana
`C_in → a*C_in`, `K → K+ln(a)` pozostawia ten sam C_out. Jeśli niezmierzony
wlot może zmieniać się w czasie, taką kompensację można wykonać punkt po
punkcie. Znany wlot lub mocne, sprawdzalne ograniczenia jego modelu mogą tę
niejednoznaczność zmniejszyć; sama elastyczna sieć ML jej nie rozwiązuje.
Przy stałej geometrii i wlocie bogate wymuszenie elektryczne pomagałoby
rozróżniać parametry, ale obecnego archiwum nie można uznać za taki eksperyment.

Ilustracja syntetyczna, nie dane instalacji: C_in=1000, K=4,6 oraz
C_in=2000, K=4,6+ln(2) dają identyczny wylot 10,052 jednostki. Po hipotetycznym
pomnożeniu K przez 1,1 przewidują odpowiednio 6,346 i 5,921. Zgodność w stanie
referencyjnym nie gwarantuje zgodnej odpowiedzi scenariuszowej. Dodatkowo
przemnożenie A przez b i podzielenie w przez b nie zmienia K.

Dlatego nie dopasowujemy jednocześnie swobodnego C_in(t), rho(t), grubości
osadu, osobnych sprawności pól i elastycznej korekty ML. Wysokie R² mogłoby
wtedy współistnieć z dowolnymi „parametrami fizycznymi”. Badania kalibracji
zwracają uwagę na zależność wyników od modelu rozbieżności i nieidentyfikowalność:
[Ling, Mullins i Mahadevan, 2014](https://doi.org/10.1016/j.jcp.2014.08.005).

## 5. Co może wyjść, a czego ten projekt nie udowodni

| Rezultat | Ocena obecnie | Jak go sprawdzić |
| --- | --- | --- |
| Model stężenia pyłu z procesu, elektryki i rappingu | Wykonalny pilotaż | Chronologia, wspólne originy i silne baselines |
| Lepsza odporność na brak fragmentu reżimu treningowego | Hipoteza o istotnym potencjale | Celowo wyłączone zakresy obciążenia/przepływu, ocena na pomiarach |
| Mniejsze zapotrzebowanie na historię | Testowalna hipoteza | Krzywe uczenia na całych blokach dni, bez zmiany testu |
| Mapa błędu, pokrycia i odmowy predykcji | Wykonalny rezultat metodologiczny | Ocena błędu i przedziałów w kolejnych reżimach |
| Analiza wrażliwości energii i pyłu w modelu | Warunkowy wynik symulacyjny | Kilka rodzin założeń; jawna stabilność/niestabilność scenariuszy |
| Wskazanie najbardziej wartościowego dodatkowego pomiaru | Wykonalne w symulacji | Redukcja niejednoznaczności po ujawnieniu wlotu/geometrii w eksperymencie syntetycznym |
| Prawdziwa rho, masa osadu, sprawność poszczególnych pól | Brak uzasadnienia z obecnego archiwum | Potrzebna niezależna informacja kotwicząca te parametry |
| Wiarygodne predykcje daleko poza całą historią | Brak empirycznej walidacji | Nowe dane albo niezależnie zweryfikowany model fizyczny |
| PID, bezpieczne nastawy, potwierdzone oszczędności X% | Nie wynik tego protokołu | Osobne dane o działaniu, granicach i walidacji instalacyjnej |
| Rozpoznawanie rzeczywistych awarii | Nie wynika z samych reszt | Etykiety lub niezależne potwierdzenie usterek |

„Nie udowodni” dotyczy obecnych informacji i metody, nie twierdzenia, że ESP
nie ma potencjału oszczędności. Nie istnieje wiarygodny procent poprawy,
który można obecnie obiecać.

## 6. Wartość naukowa i stan literatury

Przegląd był ukierunkowany, wykonany 2026-09-14; **nie jest systematycznym
przeglądem ani potwierdzeniem pierwszeństwa**. Korzystano ze źródeł pierwotnych
oraz opracowań technicznych EPA; zakres dostępu zaznaczono poniżej.

| Źródło | Co sprawdzono i co to oznacza dla projektu |
| --- | --- |
| [Guo i in., 2018, Powder Technology 340, 163–172](https://doi.org/10.1016/j.powtec.2018.09.017) | Abstrakt i podgląd wydawcy. Model mechanizmu ESP połączono już z korektą uczoną z danych, korzystając także z parametrów projektowych. Walidacyjne R² hybrydy 0,887 wobec 0,867 mechanizmu i 0,857 DNN to wynik tamtego zbioru, nie prognoza naszego. |
| [Li i in., 2013, Journal of Process Control 23, 1041–1051](https://doi.org/10.1016/j.jprocont.2013.06.007) | Abstrakt/podgląd i opis autora. Dobór napięć wielu pól przy ograniczeniu pyłu i minimalizacji mocy też był badany. Sam algorytm optymalizacyjny nie stanowi nowości. |
| [EPA, Mathematical Model of Electrostatic Precipitation, Revision 1, vol. I](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=9100R8RJ.TXT) | Rozdział o reemisji: model uwzględnia straty rappingowe, ale zaznacza ograniczenia dynamiczne. Uzasadnia osobny moduł rappingu, nie przeniesienie jego parametrów na nasz ESP. |
| [Kennedy i O’Hagan, 2001](https://doi.org/10.1111/1467-9868.00294) | Abstrakt wydawcy: kalibracja i rozbieżność model–obiekt są odrębnymi składnikami modelowania niepewności. |
| [Ling, Mullins i Mahadevan, 2014](https://doi.org/10.1016/j.jcp.2014.08.005) | Abstrakt/podgląd wydawcy: wybór modelu rozbieżności wpływa na kalibrację i identyfikowalność. |

Moja ocena potencjalnego wkładu, **nie ocena już osiągniętej nowości**:

| Podejście | Siła potencjalnego wkładu |
| --- | --- |
| Kolejny model piku lub detektor reszt bez walidacji użyteczności | Ograniczona; łatwo odtwarza harmonogram |
| Dołączenie równania fizycznego i niewielka poprawa MAE | Umiarkowana, raczej przyrostowa; podobne prace istnieją |
| Hybryda + testy nowych dla treningu reżimów + kontrola błędnej fizyki + niepewność i identyfikowalność | Wyraźnie mocniejsze pytanie metodologiczne; dobry kandydat na rozdział/artykuł, jeśli wyniki są przekonujące |
| Transfer na drugi okres/obiekt lub walidacja interwencji energetycznej | Najmocniejsza walidacja zewnętrzna; obecnie brak danych do jej wykonania |

Sama fizyka nie czyni pracy naukowo lepszą od rzetelnej diagnostyki. Wartość
zwiększą falsyfikowalne hipotezy, porównania z równie dobrze przygotowanym ML,
analiza kiedy model zawodzi i rozdzielenie błędu symulatora od błędu obiektu.
Jeden wielokrotnie oglądany miesiąc nie daje automatycznie kompletnego doktoratu.
Także negatywny wynik może mieć znaczenie, jeśli pokaże, które ograniczenia
strukturalne uniemożliwiają wiarygodne scenariusze i jaka informacja je usuwa.

Proponowany temat roboczy:

> Hybrydowe modelowanie przemysłowego elektrofiltru przy ograniczonej
> obserwowalności: uogólnianie między reżimami pracy i ocena niepewności
> scenariuszy energetyczno-emisyjnych.

## 7. Decyzja implementacyjna

Najpierw H0–H2: kontrakt i identyfikowalność, testy syntetyczne, mały model
z ograniczeniami fizycznymi i uczoną korektą na D1. Bez CFD, PINN, RL,
optymalizatora nastaw ani dużej bazy danych syntetycznych.
H3 poszerza walidację o D2/D3 i wyłączone reżimy. Dopiero H4 bada warunkowe
scenariusze oraz wartość dodatkowej informacji.

Oszczędność energetyczna pozostaje motywacją długofalową. Najbliższy wynik
użytkowy to mapa **gdzie model trafnie przewiduje, gdzie nie ma danych, a gdzie
wynik zależy głównie od założeń fizycznych**. Taką mapę można wykorzystać do
planowania pomiarów i przyszłego eksperymentu; nie jest mapą bezpiecznych nastaw.

Korekta wcześniejszych wypowiedzi w rozmowie: nie zostaje wyłącznie diagnostyka,
ale też nie można po prostu wyestymować rho jako stanu ukrytego i uznać, że
poszerzono wiarygodny zakres instalacji. Ten protokół bada dokładnie tę granicę.
