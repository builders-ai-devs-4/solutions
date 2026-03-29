import os
import re
import sys
import time
from typing import Optional
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import requests

from libs.central_client import _post_to_central
from modules.models import SubmitAnswerInput

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.loggers import agent_logger

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]

FLAG_RE = re.compile(r"\{FLG:[^}]+\}")
ECCS_RE = re.compile(r"ECCS-[A-Za-z0-9]{40,}")
MAX_TOOL_ITERATIONS = 20
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 10 + 2  # 202

    
@tool(args_schema=SubmitAnswerInput, response_format="content_and_artifact")
def submit_answer(**kwargs) -> tuple[str, dict]:
    """
    Submit the final answer to the central verification endpoint.
    Call this only when you have the complete and confirmed answer ready.
    After calling this tool, ALWAYS call scan_flag on the response.
    """
    values = list(kwargs.values())
    answer = values[0] if len(values) == 1 else kwargs
    return _post_to_central(answer)

@tool
def scan_flag(text: str) -> Optional[str]:
    """
    Search for a success flag matching the pattern {FLG:...} in the given text.
    Call this tool to analyze the server's response after submitting a solution to verify task completion.
    """
    match = FLAG_RE.search(text)
    if match:
        agent_logger.info(f"[FLAG FOUND] {match.group(0)}")
        return match.group(0)
    agent_logger.info(f"[scan_flag] no flag in text (len={len(text)})")
    return None
