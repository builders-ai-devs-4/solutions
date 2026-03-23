from pathlib import Path
import sys
from langchain_core.tools import tool
import os
from langchain.agents import create_agent
from langchain_openrouter import ChatOpenRouter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools import (
    chunk_log_by_time,
    count_prompt_tokens,
    inject_keywords_into_merge,
    keyword_log_search,
    read_file,
    save_recompressed_final,
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
compressor_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "compressor_system.md").read_text(encoding="utf-8")

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
    tools=[keyword_log_search, severity_log_filter, chunk_log_by_time],
    system_prompt=seeker_system,
    name="seeker",
)

@tool("seeker", description=(
    "Use this tool to search a very large system log file on disk. "
    "The agent saves results to disk and returns a result_json path — "
    "pass this path to subsequent tools, never request raw content. "
    "In a single call, pass ALL related keywords at once "
    "(e.g. synonyms, component IDs, related subsystems). "
    "Do NOT make separate calls for 'leak', then 'water', then 'WTANK' — "
    "pass them all in one task. "
    "Always specify which file to search: "
    "- First pass: use FAILURE_LOG path (produces severity.json) "
    "- Deep search: use severity.json from first pass (faster, preserves line references) "
    "Provide precise instruction in the 'task' parameter."
))
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

    tools=[
        read_file,                 
        save_compressed_chunk,
        merge_compressed_chunks,
        count_prompt_tokens,
        save_final_report,
        inject_keywords_into_merge,
        sort_merge_by_line_number,
        save_recompressed_final,
    ],
    system_prompt=compressor_system,
    name="compressor",
)


@tool("compressor", description=(
    "Use this tool to compress log chunks in two stages. "
    "STAGE 1: Pass a list of chunk_NNN.json file paths (from chunk_log_by_time). "
    "The agent reads each chunk, compresses every line individually, "
    "and saves chunk_NNN_compressed.json to COMPRESSED_DIR. "
    "Line numbers are preserved — they reference the original source log file. "
    "STAGE 2: The agent merges all compressed chunks, sorts by line number, "
    "counts tokens, and if over budget — re-compresses from final_report.json. "
    "Saves merged_compressed.json and final_report.log to COMPRESSED_DIR. "
    "FEEDBACK LOOP ITERATION: If Central Command requests more detail, "
    "pass new keyword chunk paths AND the existing merged_compressed.json path. "
    "Specify overwrite=False when Central asks about a NEW component not yet in merge. "
    "Specify overwrite=True when Central asks about a component ALREADY in merge "
    "that needs richer detail recovered from the source file. "
    "The agent injects new lines into the merge, sorts chronologically, "
    "then re-runs Stage 2. "
    "RE-COMPRESSION: If Supervisor rejects the result as too long, "
    "call compressor again — it re-compresses from final_report.json internally. "
    "No need to pass file paths for re-compression, just pass TOKEN_LIMIT again. "
    "Always include TOKEN_LIMIT in every call. "
    "Returns path to final_report.log. "
    "BEFORE calling send_request: read the file and verify token count "
    "with count_prompt_tokens. Only send when tokens <= TOKEN_LIMIT."
))
def call_compressor(task: str) -> str:
    result = _compressor.invoke(
        {"messages": [{"role": "user", "content": task}]},
        config=COMPRESSOR_CONFIG,
    )
    answer = result["messages"][-1].content
    agent_logger.info(f"[call_compressor] report result")
    return answer