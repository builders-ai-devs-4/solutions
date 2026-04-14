import os
import sys
import json
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]

MAX_TOOL_ITERATIONS = 20
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 10 + 2  # 202
_POLL_INTERVAL_SECONDS = 2

from libs.loggers import agent_logger
from libs.central_client import _post_to_central, _scan_flag_in_response
from modules.models import AnalyzeMapInput, CallHelicopterInput, SendActionInput, SubmitAnswerInput

from map_utils import (
    analyze_map_payload,
   )


@tool("submit_answer", args_schema=SubmitAnswerInput)
def submit_answer(action: str, destination: str | None = None) -> str:
    """
    Submit a simple action to the central API via _post_to_central.

    This tool is a thin convenience wrapper over the generic central request path.
    It should be used for actions that fit the payload shape:
    {"action": <action_name>}
    or:
    {"action": "callHelicopter", "destination": <grid_coordinate>}

    Supported usage examples include:
    - finalizing the mission with action="done"
    - retrieving central help with action="help"
    - calling the rescue helicopter with action="callHelicopter" and destination="F6"

    Args:
        action: Central action name.
        destination: Optional grid coordinate used only for helicopter dispatch.

    Returns:
        Raw response string returned by the central API.
    """
    payload = {"action": action}
    if destination is not None:
        payload["destination"] = destination
    return _post_to_central(payload)


@tool(args_schema=SendActionInput)
def send_action(
    action: str,
    type: str | None = None,
    passengers: int | None = None,
    object: str | None = None,
    where: str | None = None,
    symbol: str | None = None,
    destination: str | None = None,
    symbols: list[str] | None = None,
) -> str:
    """
    Send a single Domatowo API action to the central server and return the raw response.

    This is the generic gateway for all gameplay actions:
    - getMap
    - create
    - move
    - inspect
    - dismount
    - getObjects
    - getLogs
    - searchSymbol
    - expenses
    - actionCost
    - callHelicopter
    and others listed in the help output.
    """
    payload: Dict[str, Any] = {"action": action}
    if type is not None:
        payload["type"] = type
    if passengers is not None:
        payload["passengers"] = passengers
    if object is not None:
        payload["object"] = object
    if where is not None:
        payload["where"] = where
    if symbol is not None:
        payload["symbol"] = symbol
    if destination is not None:
        payload["destination"] = destination
    if symbols is not None:
        payload["symbols"] = symbols

    content = _post_to_central(payload)
    agent_logger.info(f"[send_action] payload={payload} | response={content[:200]}")
    return content

@tool("call_helicopter", args_schema=CallHelicopterInput)
def call_helicopter(destination: str) -> str:
    """
    Calls the rescue helicopter to evacuate the target from a confirmed location.

    Use this tool immediately after call_explorers returns found=True.
    The destination must be the exact coordinates reported by the explorer
    in the FOUND: <coordinates> response — do not guess or modify them.

    Args:
        destination: Grid coordinates where the helicopter should land, e.g. 'F6'.
                     Must match the field where the scout confirmed the target.

    Returns:
        Raw response string from the central API.

    Example:
        >>> call_helicopter(destination="F6")
    """
    return _post_to_central({"action": "callHelicopter", "destination": destination})


_help_cache: str | None = None

@tool(response_format="content_and_artifact")
def get_help() -> tuple[str, dict]:
    """
    Retrieve the full API documentation for the domatowo task.
    Call this first to learn all available actions and their required parameters.
    Returns documentation directly (not asynchronous, no getResult needed).
    """
    global _help_cache
    if _help_cache is not None:
        agent_logger.warning("[get_help] returning cached result — API not called again")
        return _help_cache
    
    result = _post_to_central({"action": "help"})
    _help_cache = result
    return result

@tool
def scan_flag(text: str) -> Optional[str]:
    """
    Search for a real success flag matching the pattern {FLG:XXXXX} in the given text.
    The flag must start with an alphanumeric character after 'FLG:' — placeholder text like {FLG:...} is ignored.
    Call this tool on the server's done() response to verify task completion.
    """
    flag = _scan_flag_in_response(text)
    if flag:
        agent_logger.info(f"[scan_flag] Flag found: {flag}")
        return flag
    agent_logger.info(f"[scan_flag] no flag in text={text[:200]}")
    return None


@tool(args_schema=AnalyzeMapInput)
def analyze_map(raw_map: str) -> str:
    """
    Analyze getMap response using only task data structure.
    Detect numbered tile families, select the highest active family,
    extract target fields, and build exploration clusters.
    """
    result = analyze_map_payload(raw_map)
    return json.dumps(result, ensure_ascii=False, indent=2)
