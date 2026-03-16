import time
import re
import requests
from logging import Logger
from typing import Optional

FLAG_RE = re.compile(r"\{FLG:[^}]+\}")


def _build_payload(apikey: str, task: str, action: str,
                   route: Optional[str], value: Optional[str]) -> dict:
    answer: dict = {"action": action}
    if route is not None:
        answer["route"] = route
    if value is not None:
        answer["value"] = value
    return {"apikey": apikey, "task": task, "answer": answer}


def _send(payload: dict, logger: Logger) -> requests.Response:
    """Send a single HTTP request and log the outgoing call."""
    action = payload.get("answer", {}).get("action")
    route  = payload.get("answer", {}).get("route")
    value  = payload.get("answer", {}).get("value")
    logger.info(f"[REQ] action={action} route={route} value={value}")
    return requests.post("https://hub.ag3nts.org/verify", json=payload, timeout=30)


def _log_response(resp: requests.Response, logger: Logger) -> None:
    """Log HTTP status, response headers and a body preview."""
    logger.info(
        f"[RESP] status={resp.status_code} "
        f"headers={dict(resp.headers)} "
        f"body={resp.text[:500]}"
    )


def _scan_flag(text: str, logger: Logger) -> Optional[str]:
    """Search for a {FLG:...} flag in text. Logs and returns it if found."""
    match = FLAG_RE.search(text)
    if match:
        logger.info(f"[FLAG FOUND] {match.group(0)}")
        return match.group(0)
    return None


def _wait_for_rate_limit(resp: requests.Response, logger: Logger) -> None:
    """Read rate-limit headers and sleep for as long as the server requires."""
    retry_after = resp.headers.get("Retry-After")
    if retry_after:
        try:
            wait = float(retry_after)
            logger.warning(f"[RATE LIMIT] Retry-After={wait:.1f}s")
            time.sleep(wait)
            return
        except ValueError:
            pass

    remaining = resp.headers.get("X-RateLimit-Remaining")
    reset      = resp.headers.get("X-RateLimit-Reset")
    if remaining is not None and reset is not None:
        try:
            if int(remaining) <= 0:
                now  = int(time.time())
                rs   = int(reset)
                wait = max(1, rs - now) if rs > now else rs
                logger.warning(f"[RATE LIMIT] remaining=0, reset={rs} — sleeping {wait}s")
                time.sleep(wait)
        except (ValueError, TypeError):
            pass


def _handle_503(attempt: int, backoff: float,
                resp: requests.Response, logger: Logger) -> float:
    """Handle a 503 response: log, sleep, and return the next backoff value."""
    retry_after = resp.headers.get("Retry-After")
    wait = float(retry_after) if retry_after else backoff
    logger.warning(f"[503] attempt={attempt} — retrying in {wait:.1f}s")
    time.sleep(wait)
    return min(backoff * 2, 60)


def _handle_429(attempt: int, resp: requests.Response, logger: Logger) -> None:
    """Handle a 429 response: delegate sleep to _wait_for_rate_limit."""
    logger.warning(f"[429] attempt={attempt} — respecting rate limits")
    _wait_for_rate_limit(resp, logger)


def _parse_body(resp: requests.Response) -> dict:
    """Parse JSON body; fall back to a raw-text dict on decode failure."""
    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text}
