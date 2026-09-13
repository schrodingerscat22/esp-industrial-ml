# Wynik audytu reakcji elektrycznej po zmianie pyłu

Stan: 2026-09-13. Kod: `src/controller_response.py` i
`scripts/run_controller_response_audit.py`. Lokalny, ignorowany wynik:
`data/processed/controller_response_v1/`. Dane wejściowe miały niezmieniony
SHA-256 `686910605846534322f45d196d602bcf98fe256a93fda94edc429c081e629260`.

## Zakres

Przebieg objął 210 642 wiersze co 10 s, 24,37882 dnia obserwowanego czasu,
32 dni kalendarzowe i osiem luk. Wyliczono siedem horyzontów 10–600 s,
462 wiersze agregatów porównania modeli oraz agregaty zdarzeń dla siedmiu horyzontów. Peak
śledzonej pamięci wyniósł 0,65 GB. Nie zapisano modeli ani predykcji pojedynczych
wierszy.

## Potwierdzone obserwacje

Historia pyłu poprawia R² prognozy przyszłej zmiany mocy i średniego napięcia
ponad historię elektryczną, proces oraz wszystkie fazy rappingu. Mediany przyrostu
R² między foldami dla `P_total`/`U_mean` wynoszą odpowiednio:

| Horyzont | ΔR² moc | ΔR² napięcie |
| --- | ---: | ---: |
| 10 s | +0,072 | +0,044 |
| 30 s | +0,177 | +0,132 |
| 60 s | +0,132 | +0,101 |
| 120 s | +0,031 | +0,026 |
| 180 s | +0,008 | +0,006 |
| 300 s | −0,010 | −0,006 |
| 600 s | −0,010 | −0,003 |

Po przesunięciu cech pyłu o 30 min wewnątrz dni mediany ΔR² dla tych samych
wyników mieszczą się od −0,0022 do +0,0004. Krótkoterminowy przyrost informacji
nie jest więc odtwarzany przez ten jeden test placebo.

Lokalne projekcje z innowacją pyłu mają dodatni współczynnik dla mocy i napięcia,
największy w 60–120 s: mediany między foldami wynoszą dla mocy +0,548 i +0,588
kW na mg/Nm³ innowacji, a dla średniego napięcia +0,096 kV. Bootstrap całych dni
liczono na dziennych współczynnikach; dla horyzontów 300 i 600 s ich zakresy
obejmują zero. Nie jest to przedział dla efektu przyczynowego.

## Wyniki, które ograniczają hipotezę regulatora

W zdarzeniach zdefiniowanych przez treningowy 95./5. percentyl 60-sekundowej
zmiany pyłu wykryto 1 179 wzrostów i 1 081 spadków. Nie wystąpiła oczekiwana
symetria końcowej odpowiedzi: po wzroście pyłu dodatnia 60-sekundowa zmiana
mocy występowała w 41,2% zdarzeń, po spadku w 31,6%; mediana obu odpowiedzi
wyniosła 0,0 kW. Dla średniego napięcia udziały wyniosły 26,6% i 12,4%.

Po wykluczeniu okien działania **wszystkich** sześciu strzepywaczy nie pozostało
żadne kompletne zdarzenie. Nie można więc rozstrzygnąć, czy krótkoterminowy
sygnał pył → U/P istnieje poza harmonogramem rappingu. Jest to główne ograniczenie
tego zbioru, a nie ujemny dowód działania regulatora.

## Interpretacja

**Potwierdzone:** wskazanie pyłu wnosi krótkoterminową, stabilną między trzema
foldami informację predykcyjną dla obserwowanej odpowiedzi elektrycznej; maksimum
jest w przybliżeniu zgodne z wcześniejszym zakresem 0,5–2 min; placebo jej nie
odtwarza.

**Niepotwierdzone:** kierunkowa, symetryczna reakcja pojedynczych epizodów;
samodzielny sygnał poza rappingiem; wejście pyłomierza do regulatora; ECO,
nadmiarowe utrzymywanie mocy lub oszczędność energii.

**Alternatywy:** zaprogramowany rapping, wspólne wymuszenie procesu, fizyczna
odpowiedź ESP na zmienione własności pyłu, opóźnienie/filtracja pyłomierza i
nieobserwowane ograniczenia zasilacza.

Najjaśniejszy dozwolony wniosek brzmi: **dane są zgodne z krótkoterminową
odpowiedzią elektryczną następującą po zmianie wskazania pyłu, lecz nie pozwalają
przypisać jej regulatorowi ani traktować jako podstawy optymalizacji energii.**
