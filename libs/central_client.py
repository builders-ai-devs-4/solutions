import json, os, requests
from typing import Optional
import re
from libs.loggers import agent_logger

FLAG_RE = re.compile(r"\{FLG:[^}]+\}")
    
def _post_to_central(answer) -> tuple[str, dict]:
    """Private helper — common logic for POSTing to the central server."""
    payload = {
        "apikey": os.environ["AI_DEVS_SECRET"],
        "task":   os.environ["TASK_NAME"],
        "answer": answer,
    }
    agent_logger.info(f"[central] POST answer={str(answer)[:200]}")

    response = requests.post(os.environ["SOLUTION_URL"], json=payload, timeout=30)
    result   = response.json()

    if not response.ok:
        agent_logger.warning(f"[central] FAIL status={response.status_code} msg={result}")
        return (
            f"Central rejected the answer. "
            f"Status: {response.status_code}. "
            f"Message: {json.dumps(result, ensure_ascii=False)}. "
            f"Review the answer and retry.",
            payload,
        )

    agent_logger.info(f"[central] OK response={result}")
    return json.dumps(result, ensure_ascii=False, indent=2), payload

def _scan_flag_in_response(text: str) -> Optional[str]:
    """
    Helper function to scan for a flag in a response string.
    This is used internally after submitting an answer to check if the response contains a success flag.
    """
    match = FLAG_RE.search(text)
    if match:
        agent_logger.info(f"[FLAG FOUND] {match.group(0)}")
        return match.group(0)
    agent_logger.info(f"[scan_flag] no flag in text (len={len(text)})")
    return None