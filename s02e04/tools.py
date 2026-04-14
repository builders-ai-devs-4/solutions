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

MAILBOX_MESSAGES_DIR = os.environ["MAILBOX_MESSAGES_DIR"]
MAILBOX_HELP_DIR = os.environ["MAILBOX_HELP_DIR"]
HELP_FILE_NAME = os.environ["HELP_FILE_NAME"]


FLAG_RE = re.compile(r"\{FLG:[^}]+\}")
MAX_TOOL_ITERATIONS = 10 
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 10 + 2  # 102


@tool
def get_help_from_mailbox(action: dict = {"action": "help", "page": 1}, save_json: bool = True) -> dict:
    """
    Fetch the official API documentation and help information from the Mailbox API.
    By default, it automatically saves the output to the mailbox help directory.
    
    Returns:
        A dictionary containing the API capabilities, available actions, and required parameters.
    """
    response = _post_request_to_mailbox(action)
    agent_logger.info(f"[get_help_from_mailbox] Mailbox feedback received.")
    
    if save_json:
        # 1. Upewnij się, że katalog na pomoc istnieje przed próbą zapisu!
        Path(MAILBOX_HELP_DIR).mkdir(parents=True, exist_ok=True)
        
        # 2. Teraz bezpiecznie zapisz plik
        file_path = Path(MAILBOX_HELP_DIR) / HELP_FILE_NAME
        save_json_file(file_path, response, append=False)
        agent_logger.info(f"[get_help_from_mailbox] Mailbox feedback saved to {file_path}")
        
    return response

@tool
def read_json(file_path: str) -> dict:
    """
    Read a JSON file from the local filesystem and return its contents as a dictionary.
    Use this to inspect previously downloaded metadata or full messages.
    """
    path = Path(file_path)
    agent_logger.info(f"[read_json] Reading JSON file: {file_path}")
    
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    return json.loads(path.read_text(encoding="utf-8"))


@tool
def save_json(file_path: str, data: dict, append: bool = True) -> str:
    """
    Save a Python dictionary as a JSON file to the specified file path.
    Can append to an existing file or overwrite it.
    """
    result = str(save_json_file(file_path, data, append=append))
    agent_logger.info(f"[save_json] JSON file saved: {file_path}")
    return result

@tool
def post_action_to_mailbox(action: dict) -> dict:
    """
    Send an action payload to the Mailbox API, auto-save the result, and return the response.
    The result is automatically saved in the messages directory as `<action_name>_results.json`.
    """
    response = _post_request_to_mailbox(action)
    
    # Automatyczny, elastyczny zapis na dysk
    action_name = action.get("action", "unknown")
    
    # Upewniamy się, że folder istnieje
    Path(MAILBOX_MESSAGES_DIR).mkdir(parents=True, exist_ok=True)
    
    # Generujemy nazwę pliku na podstawie akcji, np. "search_results.json" lub "getThread_results.json"
    dynamic_filename = f"{action_name}_results.json"
    file_path = Path(MAILBOX_MESSAGES_DIR) / dynamic_filename
    
    # Zapisujemy plik (nadpisując poprzednie wyniki dla tej samej akcji, żeby nie robić bałaganu)
    save_json_file(file_path, response, append=False)
    agent_logger.info(f"[post_action_to_mailbox] Saved {action_name} results to {file_path}")

    return response

def _post_request_to_mailbox(action: dict) -> dict:
    """
    Internal helper function to send a POST request to the Mailbox API.
    Gracefully handles network errors and unexpected JSON decoding failures.
    """    
    payload = {
        "apikey": AI_DEVS_SECRET,
    }
    payload.update(action)
    
    try:
        agent_logger.info(f"[post_request_to_mailbox] Sending action to Mailbox: {json.dumps(action)}")
        response = requests.post(MAILBOX_URL, json=payload)
        
        try:
            resp_data = response.json()
        except ValueError:
            resp_data = {"error": "Invalid JSON returned by server", "raw_text": response.text}

        if not response.ok:
            agent_logger.warning(f"[post_request_to_mailbox] REJECTED (Code {response.status_code})")
            return resp_data

        agent_logger.info(f"[post_request_to_mailbox] SUCCESS")
        return resp_data
        
    except requests.exceptions.RequestException as e:
        agent_logger.error(f"[post_request_to_mailbox] Network error: {e}")
        raise RuntimeError(f"Network error while connecting to Mailbox: {e}") from e
    
    
@tool
def submit_solution(password: str, date: str, confirmation_code: str) -> dict:
    """
    Submit the extracted password, date, and confirmation code to the Central Command (Solution URL).
    Call this tool ONLY when you have successfully found ALL THREE pieces of information in the emails.
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
    """
    Search for a success flag matching the pattern {FLG:...} in the given text.
    Call this tool to analyze the server's response after submitting a solution to verify task completion.
    """
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

