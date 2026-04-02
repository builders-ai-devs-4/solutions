import os
import sys
import time
import asyncio
import aiohttp
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool

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


@tool
def queue_all_data_requests() -> str:
    """
    Queue weather, turbinecheck and powerplantcheck simultaneously using threads.
    Sends all 3 requests in parallel, returns all queuing confirmations.
    Call getResult separately afterwards to collect the results.
    """
    params = ["weather", "turbinecheck", "powerplantcheck"]
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_post_to_central, {"action": "get", "param": p}): p
            for p in params
        }
        for future in as_completed(futures):
            param = futures[future]
            results[param] = future.result()[0]
    agent_logger.info(f"[queue_all_data_requests] results={results}")
    return json.dumps(results, ensure_ascii=False)


async def _async_post(session: aiohttp.ClientSession, answer: dict) -> str:
    payload = {
        "apikey": AI_DEVS_SECRET,
        "task": TASK_NAME,
        "answer": answer,
    }
    async with session.post(SOLUTION_URL, json=payload) as resp:
        result = await resp.json()
        agent_logger.info(f"[async_post] answer={answer} response={result}")
        return json.dumps(result, ensure_ascii=False)


@tool
def queue_unlock_codes(configs: List[Dict[str, Any]]) -> str:
    """
    Queue multiple unlockCodeGenerator requests simultaneously using asyncio.
    Each config must have: startDate, startHour, windMs, pitchAngle.
    Returns all queuing confirmations. Call getResult separately to collect the codes.

    Example input:
    [
      {"startDate": "2026-04-02", "startHour": "14:00:00", "windMs": 12, "pitchAngle": 30},
      {"startDate": "2026-04-02", "startHour": "18:00:00", "windMs": 25, "pitchAngle": 90}
    ]
    """
    async def _run():
        async with aiohttp.ClientSession() as session:
            tasks = [
                _async_post(session, {"action": "unlockCodeGenerator", **cfg})
                for cfg in configs
            ]
            return await asyncio.gather(*tasks)

    results = asyncio.run(_run())
    agent_logger.info(f"[queue_unlock_codes] queued {len(configs)} unlock code requests")
    return json.dumps(results, ensure_ascii=False)