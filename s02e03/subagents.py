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
    time_window_log_search,
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

seeker_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "seeker_system.md").read_text(encoding="utf-8")
compressor_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "compressor_system.md").read_text(encoding="utf-8")

SEEKER_CONFIG = {
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": 50, 
}

_seeker = create_agent(
    model="openai:gpt-5-mini",

    tools=[keyword_log_search, severity_log_filter, time_window_log_search],
    system_prompt=seeker_system,
    name="seeker",
)

@tool("seeker", description=(
    "Use this tool to search a very large system log file on disk. "
    "IMPORTANT: In a single call, pass ALL related keywords at once "
    "(e.g. synonyms, module IDs, related subsystems). "
    "Do NOT make separate calls for 'leak', then 'water', then 'WTANK' — "
    "pass them all in one task. "
    "If you know the approximate time of the event, use time_window instead of keywords. "
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
    "recursion_limit": 50, 
}

_compressor = create_agent(
    model="openai:gpt-5-mini",

tools=[count_prompt_tokens, scan_flag, read_file],
    system_prompt=compressor_system,
    name="compressor",
)


@tool("compressor", description=(
    "Use this tool to format and compress logs. "
    "In the 'task' parameter provide THREE items: "
    "1) FILE PATH(S) to read — e.g. '/data/severity_2026-03-21.json' and '/data/keywords_result.json'. "
    "   Do NOT paste raw log lines — pass file paths only. "
    "2) The TOKEN LIMIT from your instructions. "
    "3) Compression guidelines (what to preserve based on Central feedback). "
    "Example: 'Read file at /data/severity.json and /data/keyword_result.json. "
    "Preserve info about WSTPOOL2. Token limit is 500.' "
    "The agent will read the files itself, compress and return formatted text."
))
def call_compressor(task: str) -> str:
    result = _compressor.invoke(
        {"messages": [{"role": "user", "content": task}]},
        config=COMPRESSOR_CONFIG,
    )
    answer = result["messages"][-1].content
    agent_logger.info(f"[call_compressor] report result")
    return answer