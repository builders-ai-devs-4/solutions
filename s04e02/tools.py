import os
import sys
import time
from typing import Any, Dict, Optional
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]

MAX_TOOL_ITERATIONS = 20
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 10 + 2  # 202

from libs.loggers import agent_logger
from libs.central_client import _post_to_central, _scan_flag_in_response
from modules.models import SubmitAnswerInput

@tool(args_schema=SubmitAnswerInput, response_format="content_and_artifact")
def submit_answer(answer: Dict[str, Any]) -> tuple[str, dict]:
    """
    Submit an action payload to the central API.

    Known actions (from task description):
    - {"action": "start"} — opens service window, call first
    - {"action": "config", "startDate": ..., "startHour": ..., "pitchAngle": ..., "turbineMode": ..., "unlockCode": ...} — single config point
    - {"action": "config", "configs": {"YYYY-MM-DD HH:00:00": {"pitchAngle": ..., "turbineMode": ..., "unlockCode": ...}}} — batch config
    - {"action": "done"} — validates configuration and returns flag

    Additional actions are described in API documentation retrieved via get_help().
    """
    return _post_to_central(answer)

@tool(response_format="content_and_artifact")
def get_help() -> tuple[str, dict]:
    """
    Retrieve the full API documentation for the windpower task.
    Call this first to learn all available actions and their required parameters.
    Returns documentation directly (not asynchronous, no getResult needed).
    """
    return _post_to_central({"action": "help"})

@tool
def scan_flag(text: str) -> Optional[str]:
    """
    Search for a success flag matching the pattern {FLG:...} in the given text.
    Call this tool to analyze the server's response after submitting a solution to verify task completion.
    """
    flag = _scan_flag_in_response(text)
    if flag:
        agent_logger.info(f"[scan_flag] Flag found: {flag}")
        return flag
    agent_logger.info(f"[scan_flag] no flag in text={text}")
    return None

@tool
def stopwatch(start_time: Optional[float] = None) -> float:
    """
    Simple stopwatch tool.
    - Call without arguments to record start time — returns current timestamp.
    - Call with the previously returned start_time to get elapsed seconds.
    """
    now = time.time()
    if start_time is None:
        return now
    return now - start_time