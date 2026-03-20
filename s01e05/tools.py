import os
import sys
from langchain.tools import tool
from actions import call_action
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from libs.logger import get_logger

_logger = get_logger("railway.tool")
AI_DEVS_SECRET = os.getenv("AI_DEVS_SECRET")
TASK_NAME   = os.getenv("TASK_NAME")


@tool
def railway_action(action: str, route: str = "X-01", value: str = "") -> str:
    """
    Call the railway API.
    action: one of help | reconfigure | getstatus | setstatus | save
    route:  route identifier, e.g. X-01
    value:  required only for setstatus — RTOPEN or RTCLOSE
    """
    result = call_action(
        AI_DEVS_SECRET, TASK_NAME, action, _logger,
        route=route or None,
        value=value or None,
    )
    return str(result)