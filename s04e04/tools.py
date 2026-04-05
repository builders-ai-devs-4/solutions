
import os
from pathlib import Path
import re
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
DB_PATH            = Path(os.environ["DB_PATH"])

MAX_TOOL_ITERATIONS = 20
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 10 + 2  # 202
_POLL_INTERVAL_SECONDS = 2

from libs.loggers import agent_logger
from libs.central_client import _post_to_central, _scan_flag_in_response
from database_sqlite_fts import Database
from modules.normalizer import ValidationError, _strip_pl, validate_artifacts


@tool
def normalize_city(raw: str) -> str:
    """
    Normalize a city name to ASCII title-case without Polish diacritics.
    Example: "darzlubie" -> "Darzlubie", "Łódź" -> "Lodz"
    Returns empty string if input is blank.
    """
    cleaned = _strip_pl(raw.strip())
    return cleaned.title() if cleaned else ""


@tool
def normalize_item(raw: str) -> str:
    """
    Normalize a trade item to ASCII lowercase singular nominative.
    Strips parenthetical units and leading quantities.
    Example: "łopata (10 szt)" -> "lopata", "45 workow chleba" -> "chleba"
    """
    cleaned = re.sub(r"\(.*?\)", "", raw).strip()
    cleaned = re.sub(r"^\d+\s*", "", cleaned)
    return _strip_pl(cleaned.strip()).lower()

@tool
def get_announcements_doc() -> str:
    """Fetch full source_text of the announcements document from the SQLite DB."""
    with Database(DB_PATH) as db:
        rows = db.query(
            "SELECT source_text FROM documents WHERE doc_type = \'announcements\' LIMIT 1"
        )
    if not rows:
        return "ERROR: no announcements document found"
    return rows[0]["source_text"]

@tool
def get_all_transactions() -> str:
    """
    Fetch every row from the transactions table.
    Returns JSON array of {from_city, item, to_city} objects.
    """
    with Database(DB_PATH) as db:
        rows = db.query("SELECT from_city, item, to_city FROM transactions")
    return json.dumps(rows, ensure_ascii=False)


@tool
def get_notes_doc() -> str:
    """Fetch full source_text of the conversation notes document from the SQLite DB."""
    with Database(DB_PATH) as db:
        rows = db.query(
            "SELECT source_text FROM documents WHERE doc_type = \'notes\' LIMIT 1"
        )
    if not rows:
        return "ERROR: no notes document found"
    return rows[0]["source_text"]


@tool
def log_dropped_person(name: str, reason: str) -> str:
    """
    Log a rejected person candidate — pseudonym or incomplete name.
    Call for every person skipped due to missing surname or ambiguity.
    """
    agent_logger.warning(f"[explorer_persons] dropped: name={name!r} reason={reason!r}")
    return f"logged drop: {name}"


@tool
def validate_all(cities_json: str, persons_json: str, goods_json: str) -> str:
    """
    Validate all three extracted datasets before sending to the filesystem API.
    Returns "OK" with optional warnings, or raises on critical errors.
    Input: three JSON strings for cities_demand, persons_to_cities, goods_to_cities.
    """
    try:
        cities  = json.loads(cities_json)
        persons = json.loads(persons_json)
        goods   = json.loads(goods_json)
        warnings = validate_artifacts(cities, persons, goods)
    except ValidationError as exc:
        return f"CRITICAL: {exc}"
    if warnings:
        return "OK — warnings: " + "; ".join(warnings)
    return "OK"


@tool
def fs_send(action: str) -> str:
    """
    Send a single action JSON string or a batch JSON array to the /verify/ filesystem API.
    Input must be a valid JSON string — either an object {"action": ...} or an array of objects.
    Returns the API result as a string.
    """
    try:
        payload = json.loads(action)
    except json.JSONDecodeError as e:
        return f"ERROR: invalid JSON — {e}"
    result, raw = _post_to_central(payload)
    agent_logger.info(f"[fs_send] result={result}")
    return result


@tool
def get_help_cache() -> str:
    """
    Return cached filesystem API help without calling the API again.
    Reads first from in-memory cache, then from local file cache.
    Returns an error string if cache does not exist yet.
    """
    global _help_cache

    if _help_cache is not None:
        agent_logger.info("[get_help_cache] returning in-memory cache")
        return _help_cache

    agent_logger.warning("[get_help_cache] cache is empty — get_help() was not called yet")
    return "ERROR: help cache is empty. Call get_help() earlier in task bootstrap."

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

