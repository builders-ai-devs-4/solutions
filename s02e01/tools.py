
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
from libs.generic_helpers import read_file_base64, read_file_text, save_file
import tiktoken
# gpt-5
# gpt-5-mini

# {
#     "code": -960,
#     "message": "Prompt rejected due to security policy.",
#     "balance": 1.5
# }

FLAG_RE = re.compile(r"\{FLG:[^}]+\}")

def scan_flag(text: str, logger: Logger) -> Optional[str]:
    """Search for a {FLG:...} flag in text. Logs and returns it if found."""
    match = FLAG_RE.search(text)
    if match:
        logger.info(f"[FLAG FOUND] {match.group(0)}")
        return match.group(0)
    return None
   
@tool
def save_file_from_url(url: str, folder: Path) -> Path | None:
    """ Download a file from a URL and save it to the specified folder. Returns the path to the saved file."""
    return save_file(url, folder)

def encode_prompt(prompt: str, model_name: str) -> Tuple[list[int], int]:
    '''Encodes the prompt using the specified model's tokenizer and 
    returns the list of token IDs and the token count.'''
    
    encoding_name = tiktoken.encoding_name_for_model(model_name)
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(prompt)
    return tokens, len(tokens)


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
