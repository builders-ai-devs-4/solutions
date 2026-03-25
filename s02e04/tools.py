from pathlib import Path
import re
import sys
from typing import Optional
from langchain_core.tools import tool
import os
import requests
from modules.tiktoken import encode_prompt
from datetime import datetime, date
from modules.models import SolutionUrlRequest, AnswerModel


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from libs.filetype_detect import detect_file_type
from libs.generic_helpers import get_filename_from_url, read_file_base64, read_file_text, save_file, save_json_file
from loggers import agent_logger
import json

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL        = os.environ["SOLUTION_URL"]

DATA_FOLDER_PATH    = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH  = os.environ["PARENT_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]

MAILBOX_URL = os.getenv('MAILBOX_URL')

WORKSPACE = os.getenv('WORKSPACE')
CHUNKS_DIR = os.getenv('CHUNKS_DIR')
COMPRESSED_DIR = os.getenv('COMPRESSED_DIR')
MAILBOX_HELP_DIR = os.getenv("MAILBOX_HELP_DIR")

FLAG_RE = re.compile(r"\{FLG:[^}]+\}")
MAX_TOOL_ITERATIONS = 10 
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 10 + 2  # 102


from langchain_core.tools import tool
from loggers import agent_logger

@tool
def get_help_from_mailbox(action = {"action": "help",
        "page": 1}, save_json = True) -> dict:
    """
    Fetch help information from the mailbox.
    Returns:
        A dictionary containing the help information.
    """
    
    response = _post_request_to_mailbox(action)
    if save_json:
        file_path = Path(MAILBOX_HELP_DIR) / "mailbox_help.json"
        save_json_file(file_path, response.json())
    return response.json()

@tool
def read_json(file_path: str) -> dict:
    """Read a JSON file and return its contents as a dictionary."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    return json.loads(path.read_text(encoding="utf-8"))

@tool
def post_action_to_mailbox(action: dict) -> dict:
    """
    Send an action to Mailbox and return its response.
    Args:
        action: A dictionary containing the action details (e.g., {"action": "getInbox", "page": 1}).
    Returns:
        A dictionary containing Mailbox's response (e.g., inbox data or feedback).
    """
    response = _post_request_to_mailbox(action)
    try:
        feedback = response.json()
        agent_logger.info(f"[post_action_to_mailbox] Mailbox feedback: {feedback}")
        return feedback
    except ValueError:
        agent_logger.error(f"[post_action_to_mailbox] Invalid JSON response: {response.text}")
        raise ValueError(f"Invalid JSON response from Mailbox: {response.text}")


def _post_request_to_mailbox(action: dict) -> dict:
    """
    Internal helper function to send a POST request to the Mailbox with the given action.
    Handles errors gracefully and logs all interactions.
    """    

    # 2. Payload structure
    payload = {
        "apikey": os.getenv("AI_DEVS_SECRET"),
    }
    payload.update(action)  # Merge the action dict into the payload
    
    # 3. Send and 'soft' error logging
    try:
        agent_logger.info(f"[post_request_to_mailbox] Sending answer to Mailbox {(json.dumps(action))}")
        response = requests.post(MAILBOX_URL, json=payload)
        
        # Try to extract JSON and the message from Mailbox
        try:
            resp_data = response.json()
            mailbox_message = resp_data.get("message", response.text)
        except ValueError:
            mailbox_message = response.text
        # Instead of raising an exception and exiting, return feedback to the agent
        if not response.ok:
            agent_logger.warning(f"[post_request_to_mailbox] REJECTED (Code {response.status_code}): {mailbox_message}")
            return resp_data

        agent_logger.info(f"[post_request_to_mailbox] SUCCESS: {mailbox_message}")
        return resp_data
        
    except requests.exceptions.RequestException as e:
        agent_logger.error(f"[post_request_to_mailbox] Network error: {e}")
        raise RuntimeError(f"Network error while connecting to Mailbox: {e}") from e

@tool
def submit_solution(password: str, date: str, confirmation_code: str) -> dict:
    """
    Submit the found password, date, and confirmation code to the Central Command (Solution URL).
    Use this ONLY when you have found all three pieces of information.
    """
    
    payload = SolutionUrlRequest(
        apikey=AI_DEVS_SECRET,
        task=TASK_NAME,
        answer=AnswerModel(
            password=password,
            date=date,
            confirmation_code=confirmation_code
        )
    )
    
    agent_logger.info(f"[submit_solution] Sending payload: {payload.model_dump_json()}")
    
    response = requests.post(SOLUTION_URL, json=payload.model_dump())
    
    try:
        result = response.json()
        agent_logger.info(f"[submit_solution] Response: {result}")
        return result
    except ValueError:
        agent_logger.error(f"[submit_solution] Invalid JSON response: {response.text}")
        return {"error": "Invalid response from server", "raw": response.text}

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
    
    """
    Download a file from a URL and save it to the specified folder.
    Returns the path to the saved file.

    prefix → '{prefix}_{stem}{ext}',  e.g. prefix='backup' → 'backup_failure.log'
    suffix → '{stem}_{suffix}{ext}',  e.g. suffix='2026-03-23' → 'failure_2026-03-23.log'

    Do NOT include an underscore or extension in suffix/prefix — these are added automatically.
    """
    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)
    agent_logger.info(f"[save_file_from_url] url={url} folder={folder_path}")
    path = save_file(url, folder_path, override=True, prefix=prefix, suffix=suffix)
    agent_logger.info(f"[save_file_from_url] saved_to={path}")
    return path

@tool
def get_file_list(folder: str, filter: str = "") -> list[str]:
    """Get a list of files in the specified folder, optionally filtered by a string (e.g. 'md').
    No wildcards — just a simple substring match.
    """
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
    """Read the contents of a file and return it as a string. Text files are read as UTF-8.
    Binary files (e.g., images) are read and returned as a base64-encoded string.
    """
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    info = detect_file_type(file_path)
    agent_logger.info(f"[read_file] path={file_path} kind={info.final_kind}")
    if info.final_kind == "image":
        return read_file_base64(file_path)
    else:
        return read_file_text(file_path)
    
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
    agent_logger.info(f"[count_prompt_tokens] tokens={count}")
    return count

@tool
def count_tokens_in_file(file_path: str, model_name: str = "gpt-5-mini") -> int:
    """
    Reads a file from disk and counts the number of tokens in its content.
    Use this tool to verify if a file (like final_report.log) is within the TOKEN_LIMIT.
    Returns the token count as an integer, or an error message if the file cannot be read.
    """
    if not os.path.exists(file_path):
        agent_logger.warning(f"[count_tokens_in_file] File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
        
    try:
        # Use 'replace' for errors to handle unusual characters so counting doesn't fail
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        _, count = encode_prompt(content, model_name)
        agent_logger.info(f"[count_tokens_in_file] file={file_path} tokens={count}")
        return count
        
    except Exception as e:
        agent_logger.error(f"[count_tokens_in_file] Error reading {file_path}: {e}")
        raise ValueError(f"Error reading file: {e}")

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

