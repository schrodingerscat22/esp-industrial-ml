# E1.5: audyt tagów sterowania ESP

Stan: 2026-09-12. Kod: `scripts/run_control_signal_audit.py`. Lokalny wynik
pozostaje w ignorowanym katalogu `data/processed/control_signal_audit_v1/`.
Audyt sprawdza opis metadanych i zmienność tagów; nie wyprowadza nastawy z
obserwowanego napięcia, prądu albo mocy.

## Wynik

W wersjonowanym słowniku jest 51 tagów ESP i wszystkie występują w analizowanym
zbiorze. **Nie znaleziono tagu opisanego jako wartość zadana, nastawa, limit,
stan ECO ani polecenie regulatora.** Dlatego bieżące archiwum nie zawiera
obserwowanej zmiennej interwencji potrzebnej do badania skutku zmiany nastaw na
energię lub pył.

| Grupa | Co znaleziono | Wniosek |
| --- | --- | --- |
| Trzy zespoły WN | moc, napięcia i prądy pierwotne/wtórne, częstość przeskoków | Są odpowiedziami układu, nie udokumentowanymi poleceniami sterownika. |
| Załączenie zasilaczy | Trzy potwierdzenia załączenia, każde stale równe 1 | Nie tworzą wariantu pracy. |
| Rapping | Sześć potwierdzeń pracy oraz dwa tagi trybu | Tag `008B05155` (zbiorcze) i `008B05140` (ulotowe) są stale równe 1, więc nie tworzą wariantu trybu. |
| Ogrzewanie lejów i izolatorów | Statusy i temperatury | Mogą opisywać warunki pomocnicze, lecz nie są nastawą zasilacza WN. |

Hash danych wejściowych przed i po odczycie był identyczny:
`686910605846534322f45d196d602bcf98fe256a93fda94edc429c081e629260`.
Nie zapisano danych przemysłowych do Git.

## Konsekwencja metodologiczna

Nie można teraz wiarygodnie odpowiedzieć na pytanie: „co stanie się z pyłem i
energią po obniżeniu konkretnej nastawy?”. Zmiany U/I/P są efektem pracy
zamkniętej pętli, procesu i rappingu. Nie są zarejestrowanym eksperymentem ani
naturalną zmianą polityki sterowania.

E2 ma sens wyłącznie jako diagnostyczny model stanu U–I. Nie jest kolejnym
krokiem do optymalizacji energii na obecnym archiwum. Energetyczny nurt doktoratu
wymaga co najmniej jednego z poniższych źródeł:

1. archiwum zadanych wartości, ograniczeń lub trybów regulatora z czasem ich
   zmiany;
2. drugi okres danych obejmujący celową i udokumentowaną zmianę nastaw;
3. bezpieczny eksperyment instalacyjny z ograniczeniem emisji i procedurą
   wycofania.

Bez takiego źródła rzetelny pivot to diagnostyka stanu ESP, a nie deklaracja
optymalizacji energetycznej.
