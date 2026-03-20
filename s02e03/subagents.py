from pathlib import Path
import re
import sys
from typing import Optional, Tuple
from langchain_core.tools import tool
import os
from pydantic import BaseModel, Field
import requests
from langchain_core.callbacks import BaseCallbackHandler
from modules.tiktoken import encode_prompt
from modules.models import AnswerModel, SolutionUrlRequest
from datetime import datetime, date
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools import (
    count_prompt_tokens,
    detect_mimetype,
    get_current_datetime,
    get_file_list,
    keyword_log_search,
    read_file,
    scan_flag,
    get_url_filename,
    save_file_from_url,
    _RECURSION_LIMIT,
    severity_log_filter,
)

import tiktoken
from loggers import LoggerCallbackHandler, agent_logger

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL        = os.environ["SOLUTION_URL"]

DATA_FOLDER_PATH    = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH  = os.environ["PARENT_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
FAILURE_LOG = os.getenv('SOURCE_URL1')

seeker_system = (PARENT_FOLDER_PATH / "prompts" / "seeker_system.md").read_text(encoding="utf-8")
compressor_system = (PARENT_FOLDER_PATH / "prompts" / "compressor_system.md").read_text(encoding="utf-8")

SEEKER_CONFIG = {
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": 50, 
}

_seeker = create_agent(
    model="openai:gpt-5-mini",

    tools=[keyword_log_search,severity_log_filter],
    system_prompt=seeker_system,
    name="seeker",
)

@tool("seeker", description=(
    "Użyj tego narzędzia, aby przeszukać ogromny plik logów systemowych na dysku. "
    "Nie przekazuj tu treści logów! W parametrze 'task' przekaż precyzyjną instrukcję "
    "dla agenta wyszukującego, np.: 'Znajdź wszystkie logi z błędami [WARN], [ERRO], [CRIT]' "
    "albo 'Znajdź wszystkie logi zawierające słowo kluczowe WTANK07 lub dotyczące chłodzenia'. "
    "Agent zwróci Ci surowe linie logów pasujące do kryteriów."
))
def call_seeker(task: str) -> str:
    agent_logger.info(f"[call_seeker] task={task}")
    result = _seeker.invoke(
        {"messages": [{"role": "user", "content": task}]},
        config=SEEKER_CONFIG,
    )
    answer = result["messages"][-1].content
    agent_logger.info(f"[call_seeker] {answer}")
    return answer
    
COMPRESSOR_CONFIG = {
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": 50, 
}

_compressor = create_agent(
    model="openai:gpt-5-mini",

tools=[count_prompt_tokens, scan_flag],
    system_prompt=compressor_system,
    name="compressor",
)

@tool("compressor", description=(
    "Użyj tego narzędzia do sformatowania i drastycznej kompresji surowych logów, "
    "aby zmieściły się w limicie 1500 tokenów. W parametrze 'task' musisz przekazać "
    "ZARÓWNO surowe linie logów otrzymane od Seekera, JAK I instrukcje odnośnie kompresji "
    "(np. 'Skompresuj te logi. Pamiętaj, żeby zachować informacje o podzespole WSTPOOL2, "
    "bo prosiła o to centrala: [TU WKLEJ SUROWE LINIE]'). Agent zwróci sformatowany tekst."
))
def call_compressor(task: str) -> str:
    agent_logger.info(f"[call_compressor] task={task}")
    result = _compressor.invoke(
        {"messages": [{"role": "user", "content": task}]},
        config=COMPRESSOR_CONFIG,
    )
    answer = result["messages"][-1].content
    agent_logger.info(f"[call_compressor] {answer}")
    return answer