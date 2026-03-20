import json
import logging
from pathlib import Path
import sys
from langchain_core.tools import tool
import os
from pydantic import BaseModel, Field
import requests
from langchain_core.callbacks import BaseCallbackHandler

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from libs.filetype_detect import detect_file_type
from libs.generic_helpers import read_file_base64, read_file_text, save_file

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
PARENT_FOLDER_PATH = Path(os.getenv("PARENT_FOLDER_PATH"))
PACKAGES_URL = os.getenv('POST_URL1')

import logging

class LoggerCallbackHandler(BaseCallbackHandler):
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def on_tool_start(self, serialized, input_str, **kwargs):
        self.logger.info(f"[TOOL START] {serialized.get('name')} | input: {input_str}")

    def on_tool_end(self, output, **kwargs):
        self.logger.info(f"[TOOL END] output: {str(output)[:200]}")

    def on_tool_error(self, error, **kwargs):
        self.logger.error(f"[TOOL ERROR] {error}")

    def on_llm_start(self, serialized, prompts, **kwargs):
        self.logger.debug(f"[LLM START] {serialized.get('name')}")

    def on_llm_end(self, response, **kwargs):
        self.logger.debug(f"[LLM END] {str(response)[:200]}")
        
class IndexEntry(BaseModel):
    """Structured analysis of a single file produced by the document analyst LLM."""

    summary: str = Field(
        description="2-4 sentence description of the file content and its relevance."
    )
    image_content: str = Field(
        default="",
        description="For image files: verbatim transcription of all visible text, numbers and tables. For text files: empty string."
    )
    is_form_template: bool = Field(
        default=False,
        description="True if the file contains empty placeholder fields to be filled in. False otherwise."
    )
    notes: str = Field(
        default="",
        description="Special file characteristics (e.g. restricted access, ASCII map, glossary). Empty string if none apply."
    )
    
@tool
def save_file_from_url(url: str, folder: Path) -> Path | None:
    """ Download a file from a URL and save it to the specified folder. Returns the path to the saved file."""
    return save_file(url, folder)

@tool
# def get_file_list(folder: Path | str, filter: str = None) -> list[str]:
def get_file_list(folder: str, filter: str = None) -> list[str]:
    """ Get a list of files in the specified folder, optionally filtered by a string .f.ex md. 
    No wildcards, just a simple substring match."""
    folder = Path(folder)
    if filter:
        return [f for f in folder.glob(f"*{filter}*") if f.is_file()]
    return [f for f in folder.glob("*") if f.is_file()]

@tool
# def read_file(file_path: Path | str) -> str:
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

def load_index(index_path: Path) -> dict:
    """Load the memory index from disk. Returns empty index if file does not exist."""
    if not index_path.exists():
        return {"files": {}}
    with index_path.open("r", encoding="utf-8") as f:
        return json.load(f)
