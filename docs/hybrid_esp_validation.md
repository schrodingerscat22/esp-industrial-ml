# H2: wynik pilotażu hybrydowego ESP na D1

Stan: 2026-09-14. Wdrożono H0, H1 i H2 wyłącznie na D1 według
[hybrid_esp_methodology.md](hybrid_esp_methodology.md) i
[hybrid_esp_handoff.md](hybrid_esp_handoff.md). Nie wykonano H3 ani H4.
Nie zapisano modeli, predykcji jednostkowych ani szczegółowych szeregów.
Wyniki lokalne pozostają w ignorowanym `data/processed/hybrid_esp_h2_d1_v3/`.

## Co wdrożono

- `src/hybrid_esp.py`: sześć przyczynowych historii rappingu z trzema jądrami
  30/120/300 s, rdzeń z dodatnim efektywnym parametrem `a`, addytywnymi
  amplitudami rappingu `b>=0` oraz wymuszonymi lukami/pamięcią 15 min.
- `src/hybrid_esp_validation.py`: podział fit/kalibracja/D1, wspólne metryki
  i mapa wsparcia cech; nie jest ona dowodem fizycznej poprawności modelu.
- `scripts/run_hybrid_esp_audit.py`: manifest, kontrola hash, etapowe agregaty,
  smoke oraz pełny D1. Artefakty zawierają tylko konfigurację i agregaty.
- Test bilansu syntetycznego, granic, ostatniego pola, nakładających się
  rappingów, luki/NaN, niejednoznaczności C_in–K i A–w, chronologii D1,
  wsparcia oraz braku wpływu przyszłej mutacji na wcześniejsze dopasowanie.

Jądro rappingu jest splotem osobno w każdym ciągłym segmencie czasu. Jest
równoważne sumie przesuniętych obserwowanych startów, lecz nie tworzy pamięci
przez lukę. Wstępna implementacja z wielokrotnym grupowaniem była zbyt wolna;
zastąpiono ją tym równoważnym splotem **przed oglądaniem metryk modelu**.

Rdzeń kalibruje się na deterministycznej, rozłożonej w czasie próbce najwyżej
1 000 originów. To ograniczenie zasobu zapisano w konfiguracji. Modele M0/M1,
uczona korekta M3 i wszystkie raportowane metryki korzystają z pełnej wspólnej
próby. Parametry rdzenia są efektywne; nie są rho, geometrią, prędkością
migracji, masą osadu ani identyfikacją regulatora.

## Kontrakt i wykonanie

Źródło: `audit_v3/df_model_clean_v1.parquet`, 210 642 wiersze, 76 kolumn.
SHA-256 przed i po przebiegu:
`686910605846534322f45d196d602bcf98fe256a93fda94edc429c081e629260`.
Porównano metadane z `dataset_clean.parquet`; szczegóły pozostają w lokalnym
manifestie. Cechy mają 64 kolumny wspólne. Po ciągłości czasu, skończoności
sygnałów oraz wymaganym rozgrzaniu 15 min pozostało 209 571 ważnych originów.

D1 rozdzielono chronologicznie: osiem dat fit, dwie kolejne daty kalibracji i
trzy daty oceny. Dwie daty kalendarzowe w zakresie D1 nie miały kompletnego
pokrycia i nie stały się sztucznymi obserwacjami. Liczności: 61 068 / 17 280 /
23 118 originów minutowych fit/kalibracja/ocena; 42 690 reszt korekty rdzenia
powstało z modeli poprzedzających oceniany dzień.

Smoke na pierwszych 360 originach oceny ukończył się w 9,2 s. Pełny D1 trwał
13,0 s, końcowy RSS procesu wyniósł 0,37 GiB, dostępny RAM 5,54 GiB, wolny dysk
13,08 GiB. To nie są maksima całego systemu, lecz potwierdzają wykonanie w
ramach projektowego limitu 2 GiB. W rdzeniu końcowym zbieżność nastąpiła po
15 ewaluacjach, lecz **14 parametrów leżało na granicy ograniczeń**. To silny
sygnał nieidentyfikowalności parametrów, niezależnie od jakości predykcji.

## Wynik D1

Główne metryki są na identycznych 23 118 originach, bez historii pyłu dla
M0–M3. P60 ma dostęp do pyłu sprzed 60 s i jest oznaczony jako pomocniczy
baseline, a nie uczciwe porównanie dostępności.

| Model | MAE mg/Nm³ | RMSE | R² | Bias | P95 AE |
| --- | ---: | ---: | ---: | ---: | ---: |
| M0: Ridge proces + rapping | 1,964 | 3,299 | 0,448 | −0,475 | 5,119 |
| M1: drzewa, wspólne cechy | **1,859** | **2,629** | **0,650** | −0,221 | 4,968 |
| M2: rdzeń ograniczony | 2,083 | 3,614 | 0,338 | −0,421 | 5,422 |
| M3: rdzeń + korekta OOF | 1,902 | 2,690 | 0,633 | −0,775 | **4,964** |
| P60: pył t−60 s | 1,832 | 4,796 | −0,166 | +0,001 | 7,000 |

M3 ma o 0,043 mg/Nm³ (2,3%) większe pełne MAE niż M1. Dzienna różnica
`MAE(M1) − MAE(M3)` ma średnią −0,064 mg/Nm³ i medianę −0,209 mg/Nm³;
bootstrap trzech całych dat daje 95% CI [−0,257; +0,276]. Dziennie M3 był
lepszy 15 lipca, lecz gorszy 12 i 16 lipca. Trzy daty to zbyt mało, aby ten
przedział uznać za dokładny lub stabilny.

Mapa wsparcia cech M1/M3 w D1 oznaczyła 95,29% originów jako `supported`,
1,78% jako `marginal` i 2,94% jako `outside`; jest to odległość od treningu,
nie walidacja fizyki. P90 bezwzględnej reszty rdzenia na kalibracji wyniosło
5,04 mg/Nm³. Przedziałów nie stosowano jako alarmów ani limitów emisji.

## Wniosek i następna bramka

**H2 nie potwierdza H-G.** W jednym rozwojowym foldzie model hybrydowy nie
poprawił MAE względem równie przygotowanego modelu danych, a parametry rdzenia
są słabo określone przez ograniczenia. Nie znaczy to, że fizyka ESP jest błędna
ani że na instalacji nie ma efektów fizycznych. Znaczy, że ten konkretny,
redukowany rdzeń i dostępne sygnały nie uzyskały jeszcze przewagi predykcyjnej.

Wolno teraz wykonać H3, wyłącznie jako próbę falsyfikacji lub potwierdzenia na
D2/D3 i predefiniowanych wyłączeniach reżimów obciążenia/przepływu. Nie wolno
wykorzystać H2 do H4, do optymalizacji nastaw, do obliczenia oszczędności ani
do zgłoszenia cyfrowego bliźniaka. Jeżeli H3 nie spełni zamrożonej bramki G2,
wynik kończy hipotezę przewagi tej hybrydy na obecnym archiwum; pozostaje analiza
wsparcia, nie dalsze strojenie bez nowego uzasadnienia.
