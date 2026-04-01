import os
import sys
import time
from typing import Optional
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import requests



sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
TOOLSEARCH_URL     = os.getenv('TOOLSEARCH_URL')
HUB_URL        = os.getenv('HUB_URL')

MAX_TOOL_ITERATIONS = 20
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 10 + 2  # 202

from libs.loggers import agent_logger
from libs.central_client import _post_to_central, _scan_flag_in_response
from modules.models import FetchOkoPageInput, SubmitAnswerInput
from oko_client import get_oko_session

@tool(args_schema=SubmitAnswerInput, response_format="content_and_artifact")
def submit_answer(action: dict) -> tuple[str, dict]:
    """
    Submit an action to the central verification endpoint.
    First call with {'action': 'help'} to discover available actions and fields.
    Call with {'action': 'done'} only after all edits are confirmed.
    After calling 'done', ALWAYS call scan_flag on the response.
    """
    return _post_to_central(action)

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
    session = get_oko_session()
    resp = session.get(f"https://oko.ag3nts.org{path}")
    soup = BeautifulSoup(resp.text, "html.parser")

    # Zachowaj linki jako tekst — LLM musi je widzieć żeby nawigować
    for a in soup.find_all("a", href=True):
        a.replace_with(f"[LINK: {a.get_text(strip=True)} → {a['href']}]")

    return soup.get_text(separator="\n", strip=True)