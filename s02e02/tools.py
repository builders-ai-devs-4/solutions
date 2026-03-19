from pathlib import Path
import re
import sys
from typing import Optional, Tuple
from langchain_core.tools import tool
import os
from pydantic import BaseModel, Field
import requests
from langchain_core.callbacks import BaseCallbackHandler
from modules.grid_detector import get_grid_cells
from modules.tiktoken import encode_prompt
from modules.models import AnswerModel, RotateCellInput, SolutionUrlRequest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from libs.filetype_detect import detect_file_type
from libs.generic_helpers import get_filename_from_url, read_file_base64, read_file_text, save_file
import tiktoken
from loggers import agent_logger, api_logger

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL        = os.environ["SOLUTION_URL"]
MAP_URL             = os.environ["MAP_URL"]
MAP_RESET_URL       = os.environ["MAP_RESET_URL"]
DATA_FOLDER_PATH    = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH  = os.environ["PARENT_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]

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
    agent_logger.info(f"[scan_flag] no flag in text (len={len(text)})")
    return None
   
@tool
def get_filename(url: str) -> str:
    """Extracts a filename from a URL, using the last path segment or a default name."""
    filename = get_filename_from_url(url)
    return filename

@tool
def save_file_from_url(url: str, folder: str) -> Path | None:
    """ Download a file from a URL and save it to the specified folder. Returns the path to the saved file."""
    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)
    agent_logger.info(f"[save_file_from_url] url={url} folder={folder_path}")
    path = save_file(url, folder_path, override=True)
    agent_logger.info(f"[save_file_from_url] saved_to={path}")
    return path

@tool("rotate_cell",
      description="Rotates a single grid cell 90 degrees clockwise. Use ROW and COL index (1-3).",
      args_schema=RotateCellInput)
def rotate_cell(col: int, row: int) -> dict:
    agent_logger.info(f"[rotate_cell] input col={col} row={row}")
    payload = SolutionUrlRequest(
        apikey=AI_DEVS_SECRET,
        task=TASK_NAME,
        answer=AnswerModel(rotate=f"{col}x{row}")
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

@tool
def reset_map():
    """Sends a request to reset the map to its initial state."""
    agent_logger.info(f"[reset_map] calling {MAP_RESET_URL}")
    response = requests.get(MAP_RESET_URL)
    agent_logger.info(f"[reset_map] Map reset response: {response.status_code}")
    agent_logger.info(f"[reset_map] {response.content}")
    agent_logger.debug(f"[reset_map] Response headers: {dict(response.headers)}")
    if not response.ok:
        error_body = response.json() if response.content else {"code": response.status_code, "message": "Unknown error"}
        agent_logger.error(f"[reset_map] {response.status_code} body={error_body}")
        return error_body
    return response.status_code == 200

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
def get_grid_cells_frome_image(image_path: str) -> str:
    """Detect grid lines in the wiring diagram image, split it into cells, save them to disk, and return the folder path."""
    agent_logger.info(f"[get_grid_cells_frome_image] image_path={image_path}")
    cells_dir = get_grid_cells(image_path)
    agent_logger.info(f"[get_grid_cells_frome_image] cells_dir={cells_dir}")
    return cells_dir
