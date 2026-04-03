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
from modules.models import AnalyzeMapInput, CallHelicopterInput, SubmitAnswerInput

from map_utils import (
    analyze_map_payload,
   )

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


@tool(response_format="content_and_artifact")
def get_help() -> tuple[str, dict]:
    """
    Retrieve the full API documentation for the domatowo task.
    Call this first to learn all available actions and their required parameters.
    Returns documentation directly (not asynchronous, no getResult needed).
    """
    return _post_to_central({"action": "help"})

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

@tool
def send_action(payload: Dict[str, Any]) -> str:
    """
    Sends a single action to the game API and returns the result immediately.
    Use for all game actions: create, move, inspect, getLogs, getMap, help.

    Args:
        payload: Action payload dict, e.g.:
            {"action": "inspect", "field": "F6"}
            {"action": "move", "direction": "N"}

    Returns:
        JSON string with the API response.

    Example:
        >>> send_action({"action": "inspect", "field": "F6"})
        >>> send_action({"action": "create", "type": "transporter", "passengers": 2})
    """
    content, _ = _post_to_central(payload)
    agent_logger.info(f"[send_action] payload={payload} | response={content[:200]}")
    return content


@tool(args_schema=AnalyzeMapInput)
def analyze_map(raw_map: str) -> str:
    """
    Analyze getMap response using only task data structure.
    Detect numbered tile families, select the highest active family,
    extract target fields, and build exploration clusters.
    """
    result = analyze_map_payload(raw_map)
    return json.dumps(result, ensure_ascii=False, indent=2)

# @tool
# def analyze_map(raw_map: str) -> str:
#     """
#     Parses the raw map response from getMap, identifies tall buildings,
#     groups them into spatial clusters, and returns drop points for transporters.

#     Call this immediately after send_action({'action': 'getMap'}) to get
#     a structured cluster plan ready for call_explorers.

#     Args:
#         raw_map: Raw response string from getMap action.

#     Returns:
#         JSON string with list of clusters, each containing:
#             cluster_id (int): cluster index (0-based)
#             blocks (list[str]): grid coordinates of tall buildings, e.g. ['F6', 'F7']
#             drop_point (str): recommended transporter drop point (centroid), e.g. 'F6'
#             block_count (int): number of tall blocks in this cluster

#     Example output:
#         [
#             {"cluster_id": 0, "blocks": ["A1", "A2", "B1"], "drop_point": "A1", "block_count": 3},
#             {"cluster_id": 1, "blocks": ["H8", "H9"], "drop_point": "H8", "block_count": 2}
#         ]
#     """
#     grid = parse_map(raw_map)
#     tall_blocks = extract_tall_blocks(grid)

#     if not tall_blocks:
#         agent_logger.warning("[analyze_map] no tall blocks found — check TALL_BLOCK_SYMBOLS")
#         return json.dumps([])

#     clusters = greedy_cluster(tall_blocks)
#     result = []

#     for idx, cluster in enumerate(clusters):
#         drop_row, drop_col = centroid(cluster)
#         cluster_data = {
#             "cluster_id": idx,
#             "blocks": [coords_to_grid(r, c) for r, c in cluster],
#             "drop_point": coords_to_grid(drop_row, drop_col),
#             "block_count": len(cluster),
#         }
#         result.append(cluster_data)
#         agent_logger.info(
#             f"[analyze_map] cluster_{idx} | "
#             f"blocks={cluster_data['blocks']} | "
#             f"drop_point={cluster_data['drop_point']}"
#         )

#     agent_logger.info(f"[analyze_map] total clusters={len(result)} | total blocks={len(tall_blocks)}")
#     return json.dumps(result, ensure_ascii=False)
