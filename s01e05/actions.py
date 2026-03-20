import os
import sys
import time
import re
import requests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logging import Logger
from typing import Optional

from helpers import _build_payload, _handle_429, _handle_503, _log_response, _parse_body, _scan_flag, _send, _wait_for_rate_limit


# ROUTE = "X-01"
#     call_action(AI_DEVS_SECRET, TASK_NAME, "reconfigure", logger, route=ROUTE)
#     call_action(AI_DEVS_SECRET, TASK_NAME, "getstatus",   logger, route=ROUTE)
#     call_action(AI_DEVS_SECRET, TASK_NAME, "setstatus",   logger, route=ROUTE, value="RTOPEN")
#     call_action(AI_DEVS_SECRET, TASK_NAME, "save",        logger, route=ROUTE)

FLAG_RE = re.compile(r"\{FLG:[^}]+\}")

def post_action(
    payload: dict,
    logger: Logger,
    max_retries: int = 8,
    initial_backoff: float = 1.0,
) -> dict:
    """
    POST payload with automatic retry logic:
      1. send request
      2. log response
      3. scan for flag
      4. handle error status (503 / 429)
      5. return parsed body on success
    """
    backoff = initial_backoff

    for attempt in range(1, max_retries + 1):
        # 1. send
        try:
            resp = _send(payload, logger)
        except requests.RequestException as exc:
            logger.error(f"[NET ERROR] attempt={attempt}: {exc}")
            if attempt >= max_retries:
                raise
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        # 2. log
        _log_response(resp, logger)

        # 3. scan for flag on every response (including error responses)
        _scan_flag(resp.text, logger)

        # 4. handle error statuses
        if resp.status_code == 503:
            if attempt >= max_retries:
                raise RuntimeError(f"503 after {attempt} attempts — giving up")
            backoff = _handle_503(attempt, backoff, resp, logger)
            continue

        if resp.status_code == 429:
            if attempt >= max_retries:
                raise RuntimeError(f"429 after {attempt} attempts — giving up")
            _handle_429(attempt, resp, logger)
            continue

        # 5. success — check headers as a precaution, then return
        _wait_for_rate_limit(resp, logger)
        return _parse_body(resp)

    raise RuntimeError(f"post_action: exhausted {max_retries} attempts")


def call_action(
    apikey: str, task: str, action: str, logger: Logger,
    route: Optional[str] = None, value: Optional[str] = None,
) -> dict:
    """Public API: build payload and call post_action."""
    payload = _build_payload(apikey, task, action, route, value)
    return post_action(payload, logger)