

import os
import sys


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]

from libs.central_client import _post_to_central
from libs.loggers import LoggerCallbackHandler, agent_logger

_help_cache: str | None = None

def get_help() -> tuple[str, dict]:
    """
    Retrieve the full API documentation for the domatowo task.
    Call this first to learn all available actions and their required parameters.
    Returns documentation directly.
    """
    global _help_cache
    if _help_cache is not None:
        agent_logger.warning("[get_help] returning cached result — API not called again")
        return _help_cache
    
    result, payload  = _post_to_central({"action": "help"})
    _help_cache = result
    agent_logger.info(f"[get_help] returning help result={result}")
    
    return result, payload