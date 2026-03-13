import os
from langchain.tools import tool
from helpers import call_action
from libs.logger import get_logger

_logger = get_logger("railway.tool")
_APIKEY = os.getenv("AI_DEVS_SECRET")
_TASK   = os.getenv("TASK_NAME")


@tool
def railway_action(action: str, route: str = "X-01", value: str = "") -> str:
    """
    Call the railway API.
    action: one of help | reconfigure | getstatus | setstatus | save
    route:  route identifier, e.g. X-01
    value:  required only for setstatus — RTOPEN or RTCLOSE
    """
    result = call_action(
        _APIKEY, _TASK, action, _logger,
        route=route or None,
        value=value or None,
    )
    return str(result)