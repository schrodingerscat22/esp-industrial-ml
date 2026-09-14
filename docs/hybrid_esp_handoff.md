# H: handoff do wdrożenia małego pilotażu

Stan: 2026-09-14. Instrukcja dla kolejnego zadania, możliwa do realizacji na
wcześniej używanym przez użytkownika Terra medium. Model wykonujący zadanie
ma realizować zamrożony protokół, bez ponownego projektowania celu i bez
poszerzania zakresu na własną rękę.

## 1. Co jest już wykonane

- [Studium wykonalności](hybrid_esp_feasibility.md): warunkowe GO dla modelu
  z ograniczeniami fizycznymi i walidacji między reżimami.
- [Metodologia v1](hybrid_esp_methodology.md): H0–H4 i bramki decyzyjne.
- `scripts/assess_hybrid_esp_feasibility.py`: odtwarzalny audyt podstawowego
  schematu/zmienności oraz syntetyczna tożsamość C_in–K; bez trenowania.
- Lokalny manifest: `data/processed/hybrid_esp_feasibility_20260914/preflight.json`.
- Istniejące 41 testów i `pip check` przechodzą. Modele H i ich testy fizyczne
  **jeszcze nie istnieją**; nie odczytywać tej liczby jako walidacji H.

## 2. Zakres najbliższego zlecenia

**H0 + H1 + H2 wyłącznie D1.** Kontrakt, identyfikowalność, testy syntetyczne,
M0/M1/M2/M3 i pomocnicze P60 na wspólnej próbie, raport uruchomienia. Nie
uruchamiać jeszcze H3/H4, scenariuszy zmienionego sterowania, CFD ani PINN.
Nie trenować ponownie F1–F3 i audytów E. Nie tworzyć nowego zadania w aplikacji,
chyba że użytkownik wyraźnie tego zażąda.

Przeczytać w całości:

1. `docs/research_plan.md`;
2. `docs/hybrid_esp_feasibility.md`;
3. `docs/hybrid_esp_methodology.md`;
4. ten handoff;
5. `docs/electrical_energy_validation.md` i `docs/control_signal_audit.md`.

Sprawdzić Git i instrukcje AGENTS.md. Pracować na
`codex/methodology-audit`, zachować cudze/istniejące zmiany. Dane raw/interim/
processed są tylko do odczytu jako wejścia. Nowe artefakty wyłącznie w osobnym
ignorowanym katalogu. Nie aktualizować pakietów „dla zgodności z lockiem”:
faktyczna `.venv` jest opisana w feasibility i przechodzi testy.

## 3. Proponowana struktura kodu

| Plik | Odpowiedzialność |
| --- | --- |
| `src/hybrid_esp.py` | Kontrakt parametrów, rdzeń A, jądra rappingu, wersja syntetyczna B |
| `src/hybrid_esp_validation.py` | Chronologia, reszty OOF, wsparcie, metryki i przedziały |
| `scripts/run_hybrid_esp_audit.py` | CLI, kontrola źródeł, limity, etapowe wyniki i wznowienie |
| `tests/test_hybrid_esp.py` | Testy fizyki, nieidentyfikowalności i braków |
| `tests/test_hybrid_esp_validation.py` | Dostępność czasu, foldy, OOF i wspólne originy |
| `docs/hybrid_esp_validation.md` | Rzeczywiście wykonane etapy, wyniki i decyzja o następnym kroku |

To nazwy przyszłych plików, a nie deklaracja ich istnienia.
Reużyć stałe tagów i narzędzia czasu. Nie importować maski
`controller_response.rapping_phase(...).active` jako statusu silnika: oznacza
okno 15 min po starcie. Sześć surowych statusów i historie startów mają
osobne role. Testować NaN wewnątrz ciągłej siatki, ponieważ samo `segments`
wykrywa wyłącznie przerwy znaczników.

## 4. Kolejność wykonania

1. Manifest źródeł z SHA-256, wersjami faktycznie zaimportowanych bibliotek,
   Git HEAD, parametrami i seed=42. Porównać schemat/selekcję v3 z dataset_clean.
2. Testy syntetyczne przed oglądaniem metryk przemysłowych. Jawnie nazwać
   syntetyczne geometrie i właściwości; nie przedstawiać ich jako instalacji.
3. Zbudować cechy 10 s, dopiero później wybrać originy co 60 s; raport braków
   i odrzuceń. Model wsparcia, skalowanie i parametry uczone tylko na fit.
4. Dopasować M0–M3 w ustalonej konfiguracji. Reszty do korekty M3 wyłącznie
   z chronologicznych bloków niewidzianych przez odpowiedni rdzeń.
5. Smoke na ograniczonej liczbie originów i kompletnych blokach z wymaganym
   początkiem fit. Ma nadal respektować rozdzielenie fit/kalibracja/ocena;
   jeśli nie ma dostatecznych dat, zakończyć smoke komunikatem, nie losować.
6. Pełny D1 na originach minutowych. Raportować MAE/RMSE/bias/R², rozkład po
   dniach i rappingach, wspólne pokrycie, zbieżność i niepewność zgodnie z planem.
7. Całe testy repo, kontrola SHA-256, końcowy manifest i agregaty w docs.
   H2 jest pilotem; nie ogłaszać potwierdzenia H-G ani decyzji G2 po jednym D1.

Brak możliwości interpretacji a/b nie musi blokować oceny predykcyjnej, ale
ma być jednoznacznie zapisany. Brak zbieżności/NaN blokuje dany model.
Jeśli wymagana jest zmiana istotnego założenia, najpierw zapisać ją jako
odstępstwo w metodologii, z wynikami już znanymi w chwili decyzji.

## 5. Minimalne testy o znaczeniu metodologicznym

- Zmiana przyszłego pyłu/procesu nie zmienia wcześniejszych cech, predykcji
  ani parametrów dopasowanych na wcześniejszej części danych.
- Luki czasu, NaN/Inf i nieznany rapping przerywają pamięć; powrót po luce
  wymaga rozgrzania historii. Start 0→1 nie powstaje przez lukę.
- Bilans syntetyczny: wejście = wylot + przyrost osadu + odbiór do leja
  z zadeklarowaną tolerancją dyskretyzacji; osad nigdy nie jest ujemny.
- Brak wychwytu K=0, granica silnego wychwytu, brak rappingu i rapping
  ostatniego pola zachowują granice modelu. Ostatni rapping nie ma dodatkowego
  fikcyjnego pola; wcześniejszy może być ponownie wychwycony.
- Wlot–K i A–w: różne parametry dają ten sam obserwowany wynik; procedura
  nie raportuje ich jednoznacznego odzyskania. Znany wlot i bogate wymuszenie
  w poprawnie skonstruowanej syntetyce pozwalają sprawdzić przypadek dodatni.
- Nakładające się rappingi sumują odpowiedzi; algorytm nie przypisuje
  jednej strefie całego wspólnego piku tylko dlatego, że jest najbliższa.
- Identyczne originy i transformacje dopasowane na fit; reszta OOF nie
  pochodzi z modelu, który widział odpowiadającą jej etykietę.
- Nieznany reżim/categoria daje flagę poza wsparciem; wyzerowanie korekty
  nie zamienia takiego originu w zweryfikowaną predykcję.
- Na syntetycznym obiekcie bez zależności elektrycznej procedura nie ogłasza
  odzyskania efektu elektryki. Korzystny wynik syntetyczny nie jest wynikiem
  przemysłowym i ma osobny raport.
- Stały seed daje ten sam wynik między procesami: nie wyprowadzać go
  z wbudowanego Python `hash()`, który może być losowany między uruchomieniami.

## 6. CLI i zasoby

Proponowany interfejs do zaimplementowania (obecnie jeszcze nie działa):

```powershell
.\.venv\Scripts\python.exe scripts/run_hybrid_esp_audit.py --stage preflight
.\.venv\Scripts\python.exe scripts/run_hybrid_esp_audit.py --stage synthetic
.\.venv\Scripts\python.exe scripts/run_hybrid_esp_audit.py --stage pilot --fold D1 --smoke
.\.venv\Scripts\python.exe scripts/run_hybrid_esp_audit.py --stage pilot --fold D1 --resume
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

Smoke i pełny bieg mają różne katalogi/config hashe; `--resume` dla pełnego
biegu nie może zaakceptować wyniku smoke. Pierwsze wywołanie pełnego biegu
z `--resume` może utworzyć nowy katalog, a istniejący zaakceptować tylko przy
zgodnym wejściu, wersji kodu i konfiguracji. Nie nadpisywać niezgodnych wyników.

Ograniczenia pilotażu: CPU, najwyżej dwa wątki numeryczne, jeden model naraz,
budżet RSS procesu/całego drzewa do ok. 2 GiB, lokalne artefakty do 250 MiB.
To limity projektowe, nie obietnica zmierzonego zużycia. Przy dostępnej pamięci
systemu <1 GiB zakończyć bieżący etap kontrolowanie; nie rozpoczynać kolejnego.
Używać `psutil` dla RSS i pamięci systemu; `tracemalloc` nie obejmuje całej pamięci
bibliotek numerycznych. Brak macierzy odległości N×N.

Referencje wsparcia <=20 tys. originów, dane float32 tam, gdzie to dopuszczalne,
obliczenia rdzenia/bilansu float64. Bez GPU, CFD i masowego generowania
syntetycznych przebiegów. Syntetyka w RAM, zapisywać tylko parametry i metryki.
Nie szacować czasu na podstawie poprzednich treningów; po smoke podać pomiar
czasu, RSS i uzasadniony szacunek pełnego D1.

Zapisy etapów atomowo po ukończeniu folda: konfiguracja, agregaty, `completed`
i manifest. Po restarcie wznawiać od ostatniego kompletnego etapu; nie udawać,
że kontynuowana jest przerwana iteracja fit. Nie zapisywać dużych predykcji
jednostkowych tylko po to, aby obsłużyć wznowienie. Jeśli proces uruchamiany
przez PowerShell Start-Process, użyć `-WindowStyle Hidden`.

## 7. Zakończenie zadania

Dokumentacja ma wskazać dokładnie wykonane etapy, liczbę wierszy/originów/dat,
hash danych, metryki, zasoby, wszystkie odrzucenia i ograniczenia. Oddzielić
syntetykę, wyniki na historii i hipotezy. Pokazać po polsku wynik D1 i konkretny
następny krok H3 albo techniczną przyczynę braku możliwości jego wykonania.

Zaktualizować research_plan. Zgodnie z utrzymaną zgodą użytkownika zacommitować
i wysłać kod/testy/dokumentację na `codex/methodology-audit`, bez merge do main.
Stage tylko jawnie wymienione pliki. Sprawdzić staged diff i `git check-ignore`.
Dane, modele, predykcje, szczegółowe szeregi i lokalne manifesty nie trafiają do Git.

## 8. Gotowa treść następnego zlecenia

> Wdróż H0, H1 i pilotaż H2 na D1 zgodnie z docs/hybrid_esp_handoff.md oraz
> zamrożonym docs/hybrid_esp_methodology.md. Najpierw testy syntetyczne,
> następnie smoke i pełny D1. Użyj istniejącej .venv, zachowaj dane i zmiany,
> przestrzegaj limitów zasobów. Zapisz raport, zaktualizuj plan i wyślij
> wyłącznie kod, testy i dokumentację na codex/methodology-audit. Nie
> uruchamiaj jeszcze H3/H4 i nie przedstawiaj modelu jako optymalizatora nastaw.
