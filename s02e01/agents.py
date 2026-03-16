import os
from pathlib import Path
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from tools import read_file, read_csv, save_file_from_url, scan_flag, send_to_server, count_prompt_tokens
from loggers import LoggerCallbackHandler, agent_logger
from langchain_core.callbacks import BaseCallbackHandler

META_PROMPT = (Path(__file__).parent / "promts" / "meta_prompt.md").read_text(encoding="utf-8")
CATEGORIZATION_URL = os.environ["CATEGORIZATION_URL"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]

llm = ChatOpenAI(model="gpt-4o")


MAX_TOOL_ITERATIONS = 10  # 10 zapytań + reset + pobierz CSV ~ 12 tool calls
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 2 + 2  # 22

PROMPT_ENGINEER_CONFIG = {
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": _RECURSION_LIMIT,
}

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
    "Creates or refines a DNG/NEU classification prompt. "
    "Input: task description + optionally the previous prompt and list of server errors."))
def call_prompt_engineer(task: str) -> str:
    result = _prompt_engineer.invoke(
        {"messages": [{"role": "user", "content": task}]},
        config=PROMPT_ENGINEER_CONFIG,
    )
    answer = result["messages"][-1].content
    agent_logger.info(f"[prompt_engineer] {answer}")
    return answer

# ── Subagent 2: Executor ──────────────────────────────────────────────────────

EXECUTOR_CONFIG = {
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": 50, 
    # Executor performs: 1× reset + 1× download CSV + 1× read_csv + 10× send_to_server + 10× scan_flag = ~23 tool calls → 23 * 2 + 2 = 48
}

_executor = create_agent(
    llm,
    tools=[send_to_server, save_file_from_url, read_csv, scan_flag],
    system_prompt=(
        "Wykonujesz sekwencję w tej kolejności:\n"
        "1. send_to_server(prompt='reset') — zresetuj sesję\n"
        "2. save_file_from_url(url=CATEGORIZATION_URL, folder=DATA_FOLDER_PATH) — pobierz CSV\n"
        "3. read_csv(file_path=<ścieżka do pobranego pliku>) — odczytaj wiersze\n"
        "4. Dla każdego z 10 wierszy: send_to_server(prompt=<classification_prompt z ID i opisem>)\n"
        "5. Po każdym send_to_server wywołaj scan_flag na polu 'message' z odpowiedzi.\n"
        "   Jeśli scan_flag zwróci flagę — natychmiast zatrzymaj cykl i zwróć flagę.\n"
        "6. Jeśli odpowiedź zawiera 'classification error' lub 'budget exceeded' — "
        "zatrzymaj cykl i zwróć listę błędów do supervisora.\n"
        "7. Po wysłaniu wszystkich 10 zapytań zwróć pełną listę odpowiedzi serwera.\n"
        f"CATEGORIZATION_URL={CATEGORIZATION_URL}\n"
        f"DATA_FOLDER_PATH={DATA_FOLDER_PATH}"
    ),
    name="executor",
)

@tool("executor", description=(
    "Runs the full classification cycle: reset server → download CSV → read rows → "
    "send 10 classification queries → scan each response for a flag {FLG:...}. "
    "Stops immediately if a flag is found or if server returns 'classification error'/'budget exceeded'. "
    "Input: ready-to-use classification prompt. "
    "Returns server responses or flag if found."
))
def call_executor(classification_prompt: str) -> str:
    result = _executor.invoke({"messages": [{"role": "user", "content":
        f"Wykonaj cykl używając tego promptu klasyfikacyjnego:\n\n{classification_prompt}"}]},
            config=EXECUTOR_CONFIG,
    )
    answer = result["messages"][-1].content
    agent_logger.info(f"[executor] {answer}")
    return answer
    

# --- Supervisor ---

SUPERVISOR_CONFIG = {
    "configurable": {"thread_id": "s02e01-supervisor"},
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": _RECURSION_LIMIT,
}

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
    checkpointer=InMemorySaver(),
)