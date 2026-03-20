# User Prompt: Inicjalizacja Procedury Diagnostycznej

Rozpoczynam procedurę diagnostyczną. Twoim nadrzędnym celem jest analiza logów systemowych z bieżącej zmiany i zidentyfikowanie przyczyny awarii elektrowni.

## Kontekst Operacyjny (Zmienne Zewnętrzne):
* **LIMIT_TOKENOW:** {TOKEN_LIMIT}
* **FAILURE_LOG_URL:** {FAILURE_LOG_URL}
* **SOLUTION_URL:** {SOLUTION_URL}
* **TASK_DATA_FOLDER_PATH:** {TASK_DATA_FOLDER_PATH}

## Wymagane kroki operacyjne:

1. **Inicjalizacja i Zarządzanie Plikami (KRYTYCZNE):** - Sprawdź aktualną datę i godzinę systemową.
   - Jeśli jest godzina 00:00 (lub nastąpiła zmiana dnia od ostatniego sprawdzenia), pobrane wcześniej dane uległy dezaktualizacji - musisz bezwzględnie pobrać nowy plik logów z `FAILURE_LOG_URL`.
   - Zawsze używaj dostępnych narzędzi, aby wyodrębnić bazową nazwę pliku (NAZWA_PLIKU) z adresu `FAILURE_LOG_URL`.
   - Plik logów z danego dnia musi być zawsze zapisany w katalogu `TASK_DATA_FOLDER_PATH` pod nazwą w formacie: `NAZWA_PLIKU_YYYY-MM-DD.log` (używając aktualnej daty). Sprawdź, czy taki plik już istnieje, zanim zaczniesz pobierać.
2. **Pierwsza iteracja (Faza ogólna):** Wydeleguj do agenta Seeker zadanie wyekstrahowania kluczowych zdarzeń oznaczonych jako błędy. Otrzymany wynik przekaż agentowi Compressor w celu formatowania i maksymalnej kompresji. Poinformuj Compressora o restrykcyjnym limicie wynoszącym `LIMIT_TOKENOW`.
3. **Raportowanie:** Wyślij skompresowany pakiet logów do `SOLUTION_URL` i przeprowadź analizę otrzymanej informacji zwrotnej.
4. **Pętla diagnostyczna (Iteracje szczegółowe):** Kontynuuj proces iteracyjnie. Wykorzystuj informacje z Centrali do kierowania agentem Seeker w celu pozyskiwania brakujących danych o konkretnych podzespołach. Zlecaj agentowi Compressor ponowną kompresję zaktualizowanego zestawu logów, ściśle pilnując, aby wynik nigdy nie przekroczył wartości `LIMIT_TOKENOW` przed kolejną wysyłką.

## Krytyczne ograniczenia:
* Masz całkowity zakaz bezpośredniego odczytu surowych plików logów do własnego kontekstu pamięci.
* Wszelkie operacje przeszukiwania, filtrowania i parsowania tekstu z pliku muszą być bezwzględnie delegowane do sub-agentów (Seeker i Compressor).

Procedura kończy się wyłącznie w momencie, gdy odpowiedź z Centrali będzie zawierać flagę autoryzacyjną w formacie `{FLG:...}`. Przystąp do wykonania zadania.