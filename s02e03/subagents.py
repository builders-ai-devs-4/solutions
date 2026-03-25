from pathlib import Path
import sys
from langchain_core.tools import tool
import os
from langchain.agents import create_agent
from langchain_openrouter import ChatOpenRouter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools import (
    chunk_log_by_time,
    compress_chunk,
    compress_logs,
    count_prompt_tokens,
    count_tokens_in_file,
    inject_keywords_into_merge,
    keyword_log_search,
    merge_new_logs,
    read_file,
    recompress_final,
    severity_log_filter,
    save_compressed_chunk,
    merge_compressed_chunks,
    save_final_report,
    sort_merge_by_line_number,
)

from loggers import LoggerCallbackHandler, agent_logger

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL        = os.environ["SOLUTION_URL"]

DATA_FOLDER_PATH    = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH  = os.environ["PARENT_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
FAILURE_LOG = os.getenv('SOURCE_URL1')

FAILURE_LOG = os.getenv('SOURCE_URL1')
WORKSPACE = os.getenv('WORKSPACE')
KEYWORDS_DIR = os.getenv('KEYWORDS_DIR')
SEVERITY_DIR = os.getenv('SEVERITY_DIR')
CHUNKS_DIR = os.getenv('CHUNKS_DIR')
COMPRESSED_DIR = os.getenv('COMPRESSED_DIR')

seeker_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "seeker_system.md").read_text(encoding="utf-8")
seeker_description = (Path(PARENT_FOLDER_PATH) / "prompts" / "seeker_description.md").read_text(encoding="utf-8")
compressor_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "compressor_system.md").read_text(encoding="utf-8")
compressor_description = (Path(PARENT_FOLDER_PATH) / "prompts" / "compressor_description.md").read_text(encoding="utf-8")
# | Agent      | Rekomendowany model     | Powód                                      |
# | ---------- | ----------------------- | ------------------------------------------ |
# | seeker     | openai/gpt-4.1-mini     | Dobry tool calling, tani, 1M context       |
# | compressor | google/gemini-2.0-flash | Najtańszy przy dużych kontekstach, $0.10/M |

SEEKER_CONFIG = {
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": 50, 
}

seeker_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
)

_seeker = create_agent(
    model=seeker_model,
    tools=[keyword_log_search, severity_log_filter],
    system_prompt=seeker_system,
    name="seeker",
)

@tool("seeker", description=seeker_description)
def call_seeker(task: str) -> str:
    result = _seeker.invoke(
        {"messages": [{"role": "user", "content": task}]},
        config=SEEKER_CONFIG,
    )
    answer = result["messages"][-1].content
    agent_logger.info(f"[call_seeker] report result")
    return answer
    
COMPRESSOR_CONFIG = {
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": 500, 
}


compressor_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
)
_compressor = create_agent(
    model=compressor_model,
    tools = [
        count_tokens_in_file, # Twoje nowe narzędzie do liczenia tokenów z pliku
        merge_new_logs,       # Łączy nowe znaleziska ze starymi (Krok 6)
        compress_logs         # Główny silnik roboczy (Krok 3 i rekompresja)
    ],

    system_prompt=compressor_system,
    name="compressor",
)


@tool("compressor", description=compressor_description)
def call_compressor(task: str) -> str:
    result = _compressor.invoke(
        {"messages": [{"role": "user", "content": task}]},
        config=COMPRESSOR_CONFIG,
    )
    answer = result["messages"][-1].content
    agent_logger.info(f"[call_compressor] report result")
    return answer