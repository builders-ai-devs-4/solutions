import os
import sys
import time
from typing import Optional
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
OKO_URL     = os.getenv('OKO_URL')
HUB_URL        = os.getenv('HUB_URL')
LOGIN= os.getenv('LOGIN')
PASSWORD= os.getenv('PASSWORD')

MAX_TOOL_ITERATIONS = 20
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 10 + 2  # 202

from libs.loggers import agent_logger
from libs.central_client import _post_to_central, _scan_flag_in_response
from modules.models import FetchOkoPageInput, SubmitAnswerInput
from oko_client import get_oko_session, reset_oko_session



@tool(args_schema=SubmitAnswerInput, response_format="content_and_artifact")
def submit_answer(action: str) -> tuple[str, dict]:
    """
    Submit a simple action to the central API.

    Use only for actions that require no extra fields:
    - 'help' to get API documentation
    - 'done' to finalize the task

    Do NOT pass complex payloads (like update with page/id/title/content) here.
    """
    if action not in ("help", "done"):
        raise ValueError(
            "submit_answer(action) supports only simple actions: 'help' or 'done'. "
            "For 'update', use the dedicated update tool that builds a full answer object."
        )

    return _post_to_central({"action": action})

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

@tool(args_schema=FetchOkoPageInput)
def fetch_oko_page(path: str) -> str:
    """
    Fetch a page from the OKO operator panel using an authenticated session.
    Returns page text content with links preserved.
    Start at '/' to discover available sections, then navigate deeper.
    """
    agent_logger.info(f"[fetch_oko_page] requested path={path}")

    clean_path = "/" + path.lstrip("/")
    session = get_oko_session()

    url = f"{OKO_URL}{clean_path}"
    agent_logger.info(f"[fetch_oko_page] fetching url={url}")

    resp = session.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    for a in soup.find_all("a", href=True):
        a.replace_with(f"[LINK: {a.get_text(strip=True)} → {a['href']}]")

    text = soup.get_text(separator="\n", strip=True)
    agent_logger.info(f"[fetch_oko_page] fetched url={url} chars={len(text)}")
    return text


@tool
def logout_oko_session() -> str:
    """
    Log out from the OKO web panel and reset the cached session.
    Use this when the panel shows a security warning or after finishing a run,
    before starting a fresh exploration.
    """
    agent_logger.info("[logout_oko_session] requested")

    try:
        session = get_oko_session()
    except Exception as e:
        agent_logger.warning(f"[logout_oko_session] could not obtain session: {e!r}")
        reset_oko_session()
        return f"Could not obtain session. Local cache reset. Error: {e!r}"

    if session is None:
        agent_logger.info("[logout_oko_session] no active session")
        reset_oko_session()
        return "No active OKO session to log out."

    try:
        logout_url = f"{OKO_URL}/logout"
        agent_logger.info(f"[logout_oko_session] calling logout_url={logout_url}")
        resp = session.get(logout_url, allow_redirects=True)
        agent_logger.info(
            f"[logout_oko_session] logout response status={resp.status_code} "
            f"final_url={getattr(resp, 'url', None)} "
            f"chars={len(resp.text) if getattr(resp, 'text', None) else 0}"
        )
    except Exception as e:
        agent_logger.warning(f"[logout_oko_session] error during logout request: {e!r}")
        reset_oko_session()
        return f"Logout attempted, local session cache reset. Error contacting /logout: {e!r}"

    reset_oko_session()
    agent_logger.info("[logout_oko_session] local session cache reset")

    return f"Logout called on /logout, status={resp.status_code}, local session cache reset."

@tool(response_format="content_and_artifact")
def oko_update(page: str, id: str, fields: dict) -> tuple[str, dict]:
    """
    Execute an 'update' action on the central OKO API.

    Args:
        page: Target page name as discovered from the API help or web panel (e.g. 'incydenty', 'zadania').
        id: Exact record ID string as found on the web panel.
        fields: Dictionary of fields to update, using ONLY field names returned by the API help action.
                Do NOT guess field names. Example: {"title": "...", "content": "...", "done": "YES"}
    """
    answer = {
        "action": "update",
        "page": page,
        "id": id,
        **fields,
    }
    agent_logger.info(f"[oko_update] page={page} id={id} fields={list(fields.keys())}")
    return _post_to_central(answer)