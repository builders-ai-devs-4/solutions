from pathlib import Path
import re
import sys
from typing import Optional, Tuple
from langchain_core.tools import tool
import os
from pydantic import BaseModel, Field
import requests
from langchain_core.callbacks import BaseCallbackHandler

from modules.tiktoken import encode_prompt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from libs.filetype_detect import detect_file_type
from libs.generic_helpers import read_csv_rows, read_file_base64, read_file_text, save_file
import tiktoken
from loggers import agent_logger, api_logger


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

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
CATEGORIZATION_URL = os.environ["CATEGORIZATION_URL"]
SOLUTION_URL        = os.environ["SOLUTION_URL"]

FLAG_RE = re.compile(r"\{FLG:[^}]+\}")

@tool
def scan_flag(text: str) -> Optional[str]:
    """Search for a flag in format {FLG:...} in the given text.
    Returns the flag string if found, or None if not present.
    Call this after every server response to detect task completion."""
    match = FLAG_RE.search(text)
    if match:
        agent_logger.info(f"[FLAG FOUND] {match.group(0)}")
        return match.group(0)
    return None
   
@tool
def save_file_from_url(url: str, folder: str) -> Path | None:
    """ Download a file from a URL and save it to the specified folder. Returns the path to the saved file."""
    Path(folder).mkdir(parents=True, exist_ok=True)
    return save_file(url, folder, override=True)

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
def count_prompt_tokens(prompt: str, model_name: str = "gpt-5-mini") -> int:
    """Count the number of tokens in a prompt for budget tracking."""
    _, count = encode_prompt(prompt, model_name)
    agent_logger.info(f"[count_prompt_tokens] model={model_name} tokens={count}")
    return count