
from logging import Logger
import logging
from pathlib import Path
import re
import sys
from typing import Optional, Tuple
from langchain_core.tools import tool
import os
from pydantic import BaseModel, Field
import requests
from langchain_core.callbacks import BaseCallbackHandler

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from libs.filetype_detect import detect_file_type
from libs.generic_helpers import read_csv_rows, read_file_base64, read_file_text, save_file
import tiktoken


class CategorizationAnswer(BaseModel):
    prompt: str

class CategorizationRequest(BaseModel):
    apikey: str
    task: str
    answer: CategorizationAnswer

class ServerResponse(BaseModel):
    code: int
    message: str
    balance: Optional[float] = None
    
# gpt-5
# gpt-5-mini

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
CATEGORIZATION_URL = os.environ["CATEGORIZATION_URL"]
SOLUTION_URL        = os.environ["SOLUTION_URL"]

FLAG_RE = re.compile(r"\{FLG:[^}]+\}")

_logger = logging.getLogger(__name__)

@tool
def scan_flag(text: str) -> Optional[str]:
    """Search for a flag in format {FLG:...} in the given text.
    Returns the flag string if found, or None if not present.
    Call this after every server response to detect task completion."""
    match = FLAG_RE.search(text)
    if match:
        _logger.info(f"[FLAG FOUND] {match.group(0)}")
        return match.group(0)
    return None
   
@tool
def save_file_from_url(url: str, folder: str) -> Path | None:
    """ Download a file from a URL and save it to the specified folder. Returns the path to the saved file."""
    Path(folder).mkdir(parents=True, exist_ok=True)
    return save_file(url, folder)

@tool
def get_file_list(folder: str, filter: str = None) -> list[str]:
    """ Get a list of files in the specified folder, optionally filtered by a string .f.ex md. 
    No wildcards, just a simple substring match."""
    folder = Path(folder)
    if filter:
        return [f for f in folder.glob(f"*{filter}*") if f.is_file()]
    return [f for f in folder.glob("*") if f.is_file()]

@tool
def read_file(file_path: str) -> str:
    """ Read the contents of a file and returns as a strng. Text files are read as UTF-8, 
    binary files (targeted to images) are read and returned as base64-encoded string."""
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    info = detect_file_type(file_path)
    
    if info.final_kind == "text":
        return read_file_text(file_path)
    else:
        return read_file_base64(file_path)

@tool
def read_csv(file_path: str) -> list[dict]:
    """Read a CSV file and return list of dicts with all columns as keys."""
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    return read_csv_rows(file_path)

def encode_prompt(prompt: str, model_name: str) -> Tuple[list[int], int]:
    '''Encodes the prompt using the specified model's tokenizer and 
    returns the list of token IDs and the token count.'''
    
    encoding_name = tiktoken.encoding_name_for_model(model_name)
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(prompt)
    return tokens, len(tokens)

@tool
def count_prompt_tokens(prompt: str, model_name: str = "gpt-5-mini") -> int:
    """Count the number of tokens in a prompt for budget tracking."""
    _, count = encode_prompt(prompt, model_name)
    _logger.info(f"[count_prompt_tokens] model={model_name} tokens={count}")
    return count

@tool
def send_to_server(prompt: str) -> dict:
    """Send a prompt to the solution server (SOLUTION_URL).
    Use prompt='reset' to reset the session before a new cycle.
    For classification: pass the full classification prompt with code and description embedded.
    Returns server response dict with 'code', 'message', and optionally 'balance'."""
    payload = CategorizationRequest(
        apikey=AI_DEVS_SECRET,
        task=TASK_NAME,
        answer=CategorizationAnswer(prompt=prompt),
    )
    _logger.debug(f"[send_to_server] POST {SOLUTION_URL} payload={payload.model_dump()}")
    response = requests.post(SOLUTION_URL, json=payload.model_dump())
    if not response.ok:
        error_body = response.json() if response.content else {"code": response.status_code, "message": "Unknown error"}
        _logger.error(f"[send_to_server] {response.status_code} body={error_body}")
        return error_body
    return response.json() 

