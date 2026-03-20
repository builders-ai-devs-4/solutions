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
    "Use this tool to search a very large system log file on disk. "
    "Do not pass log contents here! In the 'task' parameter provide a precise instruction "
    "for the searching agent, e.g.: 'Find all logs with errors [WARN], [ERRO], [CRIT]' "
    "or 'Find all logs containing the keyword WTANK07 or related to cooling'. "
    "The agent will return raw log lines that match the criteria."
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
    "Use this tool to format and heavily compress raw logs. "
    "In the 'task' parameter you MUST provide THREE items: "
    "1) Raw log lines obtained from the Seeker. "
    "2) The current TOKEN LIMIT you received in your instructions (e.g., in the User Prompt). "
    "3) Compression instructions and guidelines (e.g., what to preserve based on feedback from Central). "
    "Example usage: 'Compress these logs: [PASTE_LOGS_HERE]. Preserve information about WSTPOOL2. "
    "Absolute limit is [INSERT_YOUR_LIMIT] tokens.' "
    "The agent will return formatted, reduced text."
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