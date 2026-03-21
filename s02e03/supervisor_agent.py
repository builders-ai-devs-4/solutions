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

from s02e03.subagents import call_compressor, call_seeker
from tools import count_prompt_tokens, detect_mimetype, get_current_datetime, get_file_list, read_file, scan_flag, get_url_filename, save_file_from_url, _RECURSION_LIMIT, send_request

import tiktoken
from loggers import LoggerCallbackHandler, agent_logger

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL        = os.environ["SOLUTION_URL"]

DATA_FOLDER_PATH    = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH  = os.environ["PARENT_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
FAILURE_LOG = os.getenv('SOURCE_URL1')

supervisor_sys_prompt = (Path(PARENT_FOLDER_PATH) / "prompts" / "supervisor_system.md"
                     ).read_text(encoding="utf-8")

SUPERVISOR_CONFIG = {
    "configurable": {"thread_id": "s02e03-supervisor"},
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": _RECURSION_LIMIT,
}

supervisor = create_agent(
    model="openai:gpt-5-mini",
    tools=[
        save_file_from_url,
        get_url_filename,
        get_file_list,
        count_prompt_tokens,
        scan_flag,
        get_current_datetime,
        call_compressor,
        call_seeker,
        send_request

    ],
    system_prompt=supervisor_sys_prompt,
    name="supervisor",
    checkpointer=InMemorySaver(),
)
