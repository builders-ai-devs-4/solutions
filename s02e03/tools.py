from pathlib import Path
import re
import sys
from typing import Literal, Optional, Tuple
from langchain_core.tools import tool
import os
from pydantic import BaseModel, Field
import requests
from langchain_core.callbacks import BaseCallbackHandler
from modules.tiktoken import encode_prompt
from modules.models import AnswerModel, SolutionUrlRequest
from datetime import datetime, date

from s02e03.log_filters import keyword_search, severity_filter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from libs.filetype_detect import detect_file_type
from libs.generic_helpers import get_filename_from_url, read_file_base64, read_file_text, save_file
import tiktoken
from loggers import agent_logger, api_logger
import json

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL        = os.environ["SOLUTION_URL"]

DATA_FOLDER_PATH    = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH  = os.environ["PARENT_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
FAILURE_LOG = os.getenv('SOURCE_URL1')

FLAG_RE = re.compile(r"\{FLG:[^}]+\}")
MAX_TOOL_ITERATIONS = 10  # 10 requests + reset + download CSV ~ 12 tool calls
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 22 + 2  # 222


@tool
def scan_flag(text: str) -> Optional[str]:
    """Search for a flag in format {FLG:...} in the given text.
    Returns the flag string if found, or None if not present.
    Call this after every server response to detect task completion."""
    match = FLAG_RE.search(text)
    if match:
        agent_logger.info(f"[FLAG FOUND] {match.group(0)}")
        return match.group(0)
    agent_logger.info(f"[scan_flag] no flag in text (len={len(text)})")
    return None

@tool
def get_url_filename(url: str = None) -> str:
    """
    Extracts the filename from a URL string.
    Args:
        url: The URL to extract the filename from.
    Returns:
        The filename as a string.
    """
    filename = get_filename_from_url(url)
    agent_logger.info(f"[get_url_filename] filename={filename} url={url}")
    
    return filename

@tool
def save_file_from_url(url: str, folder: str, prefix: str = "", suffix: str = "") -> Path | None:
    """ Download a file from a URL and save it to the specified folder. Returns the path to the saved file."""
    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)
    agent_logger.info(f"[save_file_from_url] url={url} folder={folder_path}")
    path = save_file(url, folder_path, override=True, prefix=prefix, suffix=suffix)
    agent_logger.info(f"[save_file_from_url] saved_to={path}")
    return path

@tool
def get_file_list(folder: str, filter: str = "") -> list[str]:
    """ Get a list of files in the specified folder, optionally filtered by a string .f.ex md. 
    No wildcards, just a simple substring match."""
    folder_path = Path(folder)
    agent_logger.info(f"[get_file_list] folder={folder_path} filter='{filter}'")
    if filter:
        files = [str(f) for f in folder_path.glob(f"*{filter}*") if f.is_file()]
    else:
        files = [str(f) for f in folder_path.glob("*") if f.is_file()]
    agent_logger.info(f"[get_file_list] found={len(files)} files")
    return files

@tool
def read_file(file_path: str) -> str:
    """ Read the contents of a file and returns as a strng. Text files are read as UTF-8, 
    binary files (targeted to images) are read and returned as base64-encoded string."""
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    info = detect_file_type(file_path)
    agent_logger.info(f"[read_file] path={file_path} kind={info.final_kind}")
    if info.final_kind == "text":
        return read_file_text(file_path)
    else:
        return read_file_base64(file_path)
    
@tool
def detect_mimetype(file_path: Path) -> str:
    """Detect the MIME type of a file based on a file type detection library."""
    info = detect_file_type(file_path)
    agent_logger.info(f"[detect_mimetype] file={file_path} mime={info.mime_from_name}")
    return info.mime_from_name

@tool
def count_prompt_tokens(prompt: str, model_name: str = "gpt-5-mini") -> int:
    """Count the number of tokens in a prompt for budget tracking."""
    _, count = encode_prompt(prompt, model_name)
    agent_logger.info(f"[count_prompt_tokens] model={model_name} tokens={count}")
    return count

@tool
def get_current_datetime(cron: str) -> str:
    """
    Returns the current date, time, or full datetime as an ISO string.
    Args:
        cron: 'date' for date, 'time' for time, anything else for full datetime.
    Returns:
        ISO formatted string of the requested value.
    """
    if cron == "date":
        result = date.today().isoformat()
    elif cron == "time":
        result = datetime.now().time().isoformat()
    else:
        result = datetime.now().isoformat()
    agent_logger.info(f"[get_current_datetime] result={result} cron={cron}")
    return result


class SeverityFilterInput(BaseModel):
    file_path: str = Field(description="Path to the log file")
    output_file: str = Field(description="Path to the output JSON file")
    levels: list[str] = Field(
        default=["WARN", "ERRO", "CRIT"],
        description="List of severity levels to search for"
    )
    
class KeywordSearchInput(BaseModel):
    file_path: str = Field(
        description="Path to the log file OR JSON file from severity_filter"
    )
    keywords: list[str] = Field(
        description="List of keywords to search for (e.g. ['power','PSU','voltage'])"
    )
    mode: Literal["any", "all"] = Field(
        default="any",
        description="'any' = line contains ANY keyword, 'all' = line contains ALL keywords"
    )
    use_regex: bool = Field(
        default=False,
        description="Whether to treat keywords as regular expressions"
    )
    case_sensitive: bool = Field(
        default=False,
        description="Whether search should be case sensitive"
    )

@tool(args_schema=SeverityFilterInput)
def severity_log_filter(
    file_path: str,
    output_file: str,
    levels: list[str] = ["WARN", "ERRO", "CRIT"],
) -> dict:
    
    """
    First pass: filters logs by severity level using regex.
    Saves results to a JSON file and returns them directly.
    """
    result = severity_filter(file_path=file_path, output_file=output_file, levels=levels)
    return result

@tool(args_schema=KeywordSearchInput)
def keyword_log_search(
    file_path: str,
    keywords: list[str],
    mode: Literal["any", "all"] = "any",
    use_regex: bool = False,
    case_sensitive: bool = False,
) -> dict:
    
    """
    Searches for keywords in a log file or in a JSON file from severity_filter.
    Detects file type automatically by extension.
    """
    result = keyword_search(
        file_path=file_path,
        keywords=keywords,
        mode=mode,
        use_regex=use_regex,
        case_sensitive=case_sensitive
    )
    return result

@tool("send_request")
def send_request(compressed_logs: str) -> dict:
    """Wysyła skompresowane logi do Centrali i zwraca odpowiedź (feedback lub flagę)."""
    agent_logger.info(f"[send_request] input logs={compressed_logs}")
    
    payload = SolutionUrlRequest(
        apikey=AI_DEVS_SECRET,
        task=TASK_NAME,
        answer=AnswerModel(logs=compressed_logs)
    )
    
    response = requests.post(
        SOLUTION_URL,
        json=payload.model_dump()
    )
    
    agent_logger.info(f"[rotate_cell] sent rotate={payload.answer.rotate} status={response.status_code}")
    agent_logger.info(f"[rotate_cell] {response.content}")
    agent_logger.debug(f"[rotate_cell] Response headers: {dict(response.headers)}")
    if not response.ok:
        error_body = response.json() if response.content else {"code": response.status_code, "message": "Unknown error"}
        agent_logger.error(f"[rotate_cell] {response.status_code} body={error_body}")
        return error_body
    return response.json()

