# User Prompt: Inicjalizacja Procedury Diagnostycznej

Rozpoczynam procedurę diagnostyczną. Twoim nadrzędnym celem jest analiza logów systemowych z bieżącej zmiany i zidentyfikowanie przyczyny awarii elektrowni.

## Wymagane kroki operacyjne:

1. **Inicjalizacja:** Ustal bieżącą datę systemową i zweryfikuj, czy plik logów dla obecnego dnia znajduje się w przestrzeni roboczej (pobierz go, w przeciwnym razie).
2. **Pierwsza iteracja (Faza ogólna):** Wydeleguj do agenta Seeker zadanie wyekstrahowania kluczowych zdarzeń oznaczonych jako błędy. Otrzymany wynik przekaż agentowi Compressor w celu formatowania i maksymalnej kompresji. Bezwzględnie przestrzegaj twardego limitu 1500 tokenów.
3. **Raportowanie:** Wyślij skompresowany pakiet logów do weryfikacji przez Centralę i przeprowadź analizę otrzymanej informacji zwrotnej.
4. **Pętla diagnostyczna (Iteracje szczegółowe):** Kontynuuj proces iteracyjnie. Wykorzystuj informacje z Centrali do kierowania agentem Seeker w celu pozyskiwania brakujących danych o konkretnych podzespołach. Zlecaj agentowi Compressor ponowną kompresję zaktualizowanego zestawu logów, ściśle pilnując limitu tokenów przed każdą kolejną wysyłką.

## Krytyczne ograniczenia:

* Masz całkowity zakaz bezpośredniego odczytu surowych plików logów do własnego kontekstu pamięci.
* Wszelkie operacje przeszukiwania, filtrowania i parsowania tekstu z pliku muszą być bezwzględnie delegowane do sub-agentów (Seeker i Compressor).

Procedura kończy się wyłącznie w momencie, gdy odpowiedź z Centrali będzie zawierać flagę autoryzacyjną w formacie `{FLG:...}`. Przystąp do wykonania zadania.