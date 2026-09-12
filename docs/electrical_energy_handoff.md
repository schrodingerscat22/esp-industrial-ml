# Handoff: E1 na Terra medium

Stan: 2026-09-12. Zadanie do wykonania **później**, po zleceniu implementacji.
Metodologia: [electrical_energy_methodology.md](electrical_energy_methodology.md).
Ten dokument wyznacza zamknięty zakres, aby implementacja nie wymagała ponownego
projektowania badania przez mocniejszy model.

## Cel i definicja zakończenia

Wdrożyć E1.1–E1.3: jakość sygnałów, charakterystyki elektryczne na tle procesu,
wszystkie strzepywacze i pokrycie warunków do porównań energii. Zakończyć raportem
z decyzją A/B/C z metodologii. **Nie uruchamiać E2, F1–F3 ani treningów przy okazji.**
Brak wspólnego zakresu lub brak izolowanych zdarzeń jest poprawnym wynikiem.
Nie rozluźniać kryteriów po obejrzeniu pyłu, żeby otrzymać pozytywny rezultat.

## Co przeczytać i co już istnieje

1. Niniejszy handoff oraz sekcje 2, 4–7 i 9–11 metodologii E.
2. `docs/research_plan.md` — aktualny status projektu.
3. `src/time_analysis.py` — poprawiony czas, luki, okna, starty, pokrycie.
4. `tests/test_time_analysis.py`, `docs/methodology_audit.md` — konwencje i pułapki.
5. `notebooks/06b_voltage_variability_and_overlap_analysis.ipynb` — materiał
   historyczny; jego filtrów i definicji nie kopiować jako gotowego dowodu pokrycia.

Gałąź: `codex/methodology-audit`; na początku sprawdzić status i zachować cudze
niezacommitowane zmiany. GitHub: `schrodingerscat22/esp-industrial-ml`.
Użytkownik zezwolił na commit i push kodu, testów i dokumentacji na tę gałąź.
Nie publikować danych, szeregów czasowych, modeli ani przemysłowych outputów
notebooków. Nie przepisywać historii repozytorium.

Główne wejście: `data/processed/audit_v3/df_model_clean_v1.parquet`.
Metadane: `data/processed/tag_mapping.csv` (UTF-8, separator `;`, duplikaty nazw
tagów), ewentualnie `audit_v3/tag_classification_v1.xlsx` do kontroli.
Porównanie selekcji: `data/processed/dataset_clean.parquet` i
`data/processed/df_model_clean_v1.parquet`. Pierwszy plik zawiera też kolumnę
tekstową; wybierać jawnie sygnały, nie konwertować całej ramki do float.

Lokalny `data/processed/energy_idea_review_20260912/preflight.json` to rozpoznanie
wykonane podczas planowania. Nie jest testem akceptacji ani implementacją E1.
Starsze audyty mają inne mianowniki i konwencje okien; różnice trzeba wyjaśnić.

## Artefakty do utworzenia

- `src/electrical_state.py`: jawny schemat tagów, R_app/P_UI, flagi jakości,
  cechy podstawowego kontekstu, czas od startów wszystkich sześciu strzepywaczy.
- `src/energy_comparability.py`: pełne bloki, ekspozycja/energia, profile
  zdarzeń, wielopoziomowe porównanie i raport pokrycia.
- `scripts/run_electrical_energy_audit.py`: jeden CLI, `--stage signals|events|overlap|all`,
  `--input`, `--output-dir`, `--resume`, `--smoke`. Domyślnie wykonuje tylko E1.
- `tests/test_electrical_state.py` i `tests/test_energy_comparability.py`:
  syntetyczne dane bez zależności od lokalnych danych przemysłowych.
- `docs/electrical_energy_validation.md`: krótki wynik, mianowniki, decyzja,
  ograniczenia, lista testów i następny krok; same agregaty i wnioski.
- Aktualizacja statusu w `docs/research_plan.md` oraz metodologii E, bez
  nadpisywania historycznych wyników F i audytu 06a.

Domyślny lokalny katalog wyjść: `data/processed/electrical_energy_v1/`:

- `design.json` przed analizą: konfiguracja, wersje, seed, hash kodu i wejść;
- `signal_quality.csv`, `source_selection.json`;
- `event_summary.csv`, `event_profiles.parquet`, `overlap_counts.csv`;
- `block_summary.parquet`, `matched_pairs.parquet`, `support_summary.csv`;
- `report.json`, `run_state.json`, `execution.log`, najwyżej sześć figur PNG.

Pliki sygnałów/tagów i szczegółowe pary pozostają ignorowane przez Git.
`report.json` powinien osobno zawierać observations, hypotheses, unknowns,
gate_decision, rejection_counts i source_integrity. Brak wyniku = null/unknown
z powodem, nie zero. Nie tworzyć notebooka, dashboardu ani PDF w E1.

## Kolejność wykonania

1. Status repo, Python, zależności, wolne miejsce. Użyć istniejącego `.venv`;
   nie aktualizować pakietów bez konkretnej konieczności.
2. Spisać `design.json` z wartościami z sekcji 7 metodologii. Nową decyzję
   nieopisaną w planie oznaczyć jako interpretację i uzasadnić w raporcie.
3. Wdrożyć i sprawdzić sygnały/czas na danych syntetycznych. Zliczyć wszystkie
   przyczyny odrzuceń; nie wymagać kompletności opcjonalnych tagów dla każdej analizy.
4. Smoke: maksymalnie 20 zdarzeń i 200 bloków; nie przedstawiać jako wyniku E1.
5. Pełne etapy signals → events → overlap sekwencyjnie, z zapisem stanu po każdym.
6. Wyliczyć poziomy pokrycia i zadaną analizę czułości; raportować każdy wariant.
   Nie uruchamiać dodatkowej siatki parametrów ani nie szukać „ładnego efektu”.
7. Przygotować do sześciu wykresów: jakość/pokrycie, rozkłady U–I, sparowane
   profile zdarzeń, zależności od procesu, rozkład pokrycia par, różnice mocy
   i pyłu w parach. Oznaczyć jednostki, n zdarzeń/bloków/dni i konwencję okien.
   Obejrzeć zapisane figury; pozostawić je lokalnie.
8. Sprawdzić integralność wejść, wyniki testów, staging, format Markdown i brak
   danych w diff. Commit i push wyłącznie jawnie wymienionych kodów/testów/docs.
9. Odpowiedzieć po polsku: co stwierdzono, czy jest sens E2, czy jest pokrycie
   energetyczne, co pozostaje hipotezą, czy jakikolwiek proces nadal działa.

## Testy o znaczeniu metodologicznym

- `50 kV / 250 mA = 0,2 MΩ`; `50*250/1000 = 12,5 kW`.
- I=0, niski I, NaN, inf, ujemny znak i znane wyłączenie nie dają poprawnego R;
  unknown załączenia nie jest ani potwierdzonym on, ani potwierdzonym off.
- Wewnętrzny NaN sygnału i luka w czasie przerywają historię. Startu nie wolno
  utworzyć przez lukę, a niezaobserwowany czas od startu nie może stać się zerem.
- Pełny blok 10 min przy 12 kW ma 2 kWh; brak prawego końca lub przerwa
  wykluczają blok; punkt końcowy nie dodaje 10 s do całki.
- Brak skończonej mocy na obu końcach wyklucza przedział; sumy pól i całkowita
  energia liczone są na tej samej ekspozycji i zgadzają się algebraicznie.
- Niepełne zdarzenie jest odrzucone z powodem; inny strzepywacz jest liczony,
  a nie po cichu uznawany za niezależne zjawisko lub powód usunięcia wszystkiego.
- Syntetyczny przypadek z różnym poziomem bazowym zdarzeń odróżnia zmianę
  sparowaną od różnicy median wszystkich próbek; procent liczony per zdarzenie.
- Dopasowane pary spełniają wszystkie wybrane tolerancje, nie dzielą próbek,
  nie używają ponownie bloku, pochodzą z różnych dni; remisy są deterministyczne.
- Zmiana pyłu nie zmienia doboru par ani granic kontekstu. Odmienny proces lub
  nieznana faza nie tworzą pozornego pokrycia. Pokrycie używa godzin, nie liczby par.
- Próba bez porównywalnych bloków daje bramkę niezaliczoną i czytelny raport,
  bez awarii, dopisywania fikcyjnych oszczędności lub poluzowania warunków.
- `--resume` odmawia łączenia wyników przy innym hashu wejścia/kodu/konfiguracji.

Następnie uruchomić istniejące testy repozytorium. Do tego planu dokumentacyjnego
nie dopisywano testów; powyższe testy należą do późniejszej implementacji E1.

## Budżet obliczeń i pracy modelu

Terra medium jest proponowanym wykonawcą zgodnie z dotychczasowym wyborem
użytkownika. To podział odpowiedzialności, nie gwarancja kosztu lub jakości.
Koszt analiz lokalnych zależy od kodu, liczby wariantów i danych, a nie tylko
od modelu prowadzącego zadanie. Nie podajemy przeliczników limitu planu.

Pierwszy przebieg: jeden proces, do 2 wątków bibliotek numerycznych; projekcyjny
budżet dodatkowych artefaktów 250 MB, budżet RSS procesu 2 GB. Jeżeli prognoza
przekracza te wartości, najpierw ograniczyć kolumny i zapisy lub przetwarzać
partiami; nie kasować danych/modeli innych eksperymentów. Mierzyć RAM, czas
etapów i przyrost dysku. To ograniczenia implementacji do sprawdzenia, nie
oszacowania gwarantowanego czasu wykonania.

Oszczędzać limit przez krótkie aktualizacje po etapach, jeden raport z decyzją,
brak masowego wypisywania danych i brak wielokrotnego odczytywania całej historii
rozmowy. Mocniejszy model potrzebny dopiero przy niejednoznacznej interpretacji
wyniku lub projektowaniu interwencji. Zasada wyboru modelu przez jakość zadania
i pomiar kosztu: [OpenAI — Model selection](https://developers.openai.com/api/docs/guides/model-selection).

## Gotowe polecenie do następnego zadania

> Wdróż wyłącznie E1 z docs/electrical_energy_methodology.md zgodnie z
> docs/electrical_energy_handoff.md. Użyj dostępnych danych lokalnych, wykonaj
> testy syntetyczne, smoke i pełny audyt sekwencyjnie. Zbadaj U/I wraz z danymi
> procesu, wszystkie strzepywacze i pokrycie porównań energetycznych. Zapisz
> raport z decyzją A/B/C oraz zaktualizuj plan badań. Zachowaj istniejące zmiany
> i dane źródłowe. Monitoruj RAM oraz dodatkowe miejsce na dysku. Zacommituj
> i wyślij kod, testy i dokumentację na aktualną gałąź codex/methodology-audit;
> danych, modeli i przemysłowych outputów nie publikuj. Nie uruchamiaj E2
> ani kolejnych treningów. Wynik objaśnij krótko po polsku, także w wiadomości.
