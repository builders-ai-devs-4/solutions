import os
from pathlib import Path
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from tools import read_file, read_csv, save_file_from_url, send_to_server, count_prompt_tokens


META_PROMPT = (Path(__file__).parent / "promts" / "meta_prompt.md").read_text(encoding="utf-8")
CATEGORIZATION_URL = os.environ["CATEGORIZATION_URL"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]

llm = ChatOpenAI(model="gpt-4o")

# ── Subagent 1: Prompt Engineer ──────────────────────────────────────────────

_prompt_engineer = create_agent(
    llm,
)

_prompt_engineer = create_agent(
    llm,
    tools=[count_prompt_tokens],
    system_prompt=META_PROMPT,
    name="prompt_engineer",
)

@tool("prompt_engineer", description=(
    "Tworzy lub poprawia prompt klasyfikacyjny DNG/NEU. "
    "Wejście: opis zadania + opcjonalnie poprzedni prompt i lista błędów z serwera."))
def call_prompt_engineer(task: str) -> str:
    result = _prompt_engineer.invoke({"messages": [{"role": "user", "content": task}]})
    return result["messages"][-1].content

# ── Subagent 2: Executor ──────────────────────────────────────────────────────
_executor = create_agent(
    llm,
    tools = [send_to_server, save_file_from_url, read_csv],
    system_prompt=(
        "Wykonujesz sekwencję w tej kolejności:\n"
        "1. send_to_server(prompt='reset') — zresetuj sesję\n"
        "2. save_file_from_url(url=CATEGORIZATION_URL, folder=DATA_FOLDER_PATH) — pobierz CSV\n"
        "3. read_csv(file_path=<ścieżka>) — odczytaj wiersze\n"
        "4. Dla każdego z 10 wierszy: send_to_server(prompt=<classification_prompt + code + description>)\n"
        "5. Zwróć listę wszystkich odpowiedzi serwera.\n"
        f"CATEGORIZATION_URL={CATEGORIZATION_URL}\n"
        f"DATA_FOLDER_PATH={DATA_FOLDER_PATH}"
    ),
    name="executor",
)

def call_executor(classification_prompt: str) -> list[dict]:
    result = _executor.invoke({"messages": [{"role": "user", "content":
        f"Wykonaj cykl używając tego promptu klasyfikacyjnego:\n\n{classification_prompt}"}]})
    return result["messages"][-1].content
    

# --- Supervisor ---

supervisor = create_agent(
    llm,
    tools=[call_prompt_engineer, call_executor],
    system_prompt=(
        "Jesteś supervisorem systemu klasyfikacji DNG/NEU.\n"
        "Plan działania:\n"
        "1. Wywołaj prompt_engineer — poproś o stworzenie promptu klasyfikacyjnego.\n"
        "2. Przekaż prompt do executor — wykona cykl 10 zapytań.\n"
        "3. Jeśli executor zwróci odpowiedzi z 'classification error' lub 'budget exceeded':\n"
        "   - Przekaż błędy do prompt_engineer z prośbą o poprawę.\n"
        "   - Powtórz krok 2.\n"
        "4. Zakończ gdy wszystkie odpowiedzi są poprawne lub znajdziesz flagę {FLG:...}.\n"
        "5. Zwróć końcowy wynik i flagę jeśli obecna."
    ),
    name="supervisor",
)