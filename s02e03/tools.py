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


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from log_filters import _save_results, chunk_by_time_window, keyword_search, severity_filter, validate_compression

from libs.filetype_detect import detect_file_type
from libs.generic_helpers import get_filename_from_url, read_file_base64, read_file_text, read_json_files, save_file
import tiktoken
from loggers import agent_logger
import json

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL        = os.environ["SOLUTION_URL"]

DATA_FOLDER_PATH    = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH  = os.environ["PARENT_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]

FAILURE_LOG = os.getenv('SOURCE_URL1')
WORKSPACE = os.getenv('WORKSPACE')
KEYWORDS_DIR = os.getenv('KEYWORDS_DIR')
SEVERITY_DIR = os.getenv('SEVERITY_DIR')
CHUNKS_DIR = os.getenv('CHUNKS_DIR')
COMPRESSED_DIR = os.getenv('COMPRESSED_DIR')

FLAG_RE = re.compile(r"\{FLG:[^}]+\}")
MAX_TOOL_ITERATIONS = 10 
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 10 + 2  # 102


@tool("send_request")
def send_request(compressed_logs: str) -> dict:
    """
    Sends the final, compressed logs to the central server for verification.
    Use this tool ONLY when you have a final result from the Compressor agent
    and have confirmed it does not exceed the token limit.
    Returns the technicians' feedback or a flag.
    """
    agent_logger.info(f"[send_request] Sending logs (length: {len(compressed_logs)} chars)")
    
    payload = SolutionUrlRequest(
        apikey=AI_DEVS_SECRET,
        task=TASK_NAME,
        answer=AnswerModel(logs=compressed_logs)
    )
    
    response = requests.post(
        SOLUTION_URL,
        json=payload.model_dump()
    )
    
    agent_logger.info(f"[send_request] HTTP Status: {response.status_code}")
    
    if not response.ok:
        error_body = response.json() if response.content else {"code": response.status_code, "message": "Unknown error"}
        agent_logger.error(f"[send_request] API error: body={error_body}")
        return error_body
        
    return response.json()

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
    file_path: str = Field(
        description="Path to the source failure.log file"
    )
    levels: list[str] = Field(
        default=["WARN", "ERRO", "CRIT"],
        description="List of severity levels to filter for"
    )
    
class KeywordSearchInput(BaseModel):
    file_path: str = Field(
        description="Path to severity.json from severity_log_filter. Always pass .json — never raw .log."
    )
    keywords: list[str] = Field(
        description="List of keywords to search for (e.g. ['pump', 'WTRPMP', 'cavitation'])"
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
    levels: list[str] = ["WARN", "ERRO", "CRIT"],
) -> dict:
    """
    FIRST-PASS TOOL. Use this as the first step on failure.log.
    Filters the log keeping only lines matching severity levels (WARN/ERRO/CRIT).
    Saves results to SEVERITY_DIR/severity.log and SEVERITY_DIR/severity.json.
    Always pass severity.json (not .log) to subsequent tools to preserve
    line_number references back to the original failure.log.
    Returns: {"result_log": "...", "result_json": "..."}
    """
    output_file = str(Path(SEVERITY_DIR) / "severity")
    result = severity_filter(file_path=file_path, output_file=output_file, levels=levels)
    agent_logger.info(f"[severity_log_filter] file={file_path} output={output_file}")
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
    DEEP SEARCH TOOL. Use when the Supervisor asks about a specific subsystem or component.
    IMPORTANT: Always pass severity.json (output of severity_log_filter) — never raw .log.
    Passing .json is significantly faster and preserves line_number references to failure.log.
    Saves results to KEYWORDS_DIR/keywords.log and KEYWORDS_DIR/keywords.json.
    Returns: {"result_log": "...", "result_json": "..."}
    """
    output_base = str(Path(KEYWORDS_DIR) / "keywords")
    result = keyword_search(
        file_path=file_path,
        output_base=output_base,
        keywords=keywords,
        mode=mode,
        use_regex=use_regex,
        case_sensitive=case_sensitive,
    )
    agent_logger.info(f"[keyword_log_search] file={file_path} keywords={keywords}")
    return result

class ChunkByTimeWindowInput(BaseModel):
    file_path: str = Field(
        description="Path to .log file or .json from severity_log_filter"
    )
    output_dir: str = Field(
        description="Directory where chunk_NNN.log files will be saved"
    )
    window_minutes: int = Field(
        default=10,
        description="Size of each time window in minutes (relative to first log entry)"
    )


@tool(args_schema=ChunkByTimeWindowInput)
def chunk_log_by_time(
    file_path: str,
    output_dir: str,
    window_minutes: int = 10,
) -> dict:
    """
    PRE-PROCESSING TOOL. Splits a log file into fixed-size time chunks (chunk_NNN.log).
    Use this BEFORE sending logs to the Compressor — each chunk fits within
    the Compressor context window.
    Returns a list of chunk file paths: {"chunks": [{"chunk_index": 1, "file": "..."}]}
    """
     
    result = chunk_by_time_window(
        file_path=file_path,
        output_dir = CHUNKS_DIR,
        window_minutes=window_minutes,
    )
    agent_logger.info(
        f"[chunk_log_by_time] file={file_path} window={window_minutes}min "
        f"chunks={len(result.get('chunks', []))}"
    )
    return result


class SaveCompressedChunkInput(BaseModel):
    original_json: str = Field(
        description="Path to original chunk_NNN.json (from chunk_log_by_time)"
    )
    compressed_lines: list[dict] = Field(
        description='List of {"line_number": int, "content": str} — same count and order as original'
    )


@tool(args_schema=SaveCompressedChunkInput)
def save_compressed_chunk(original_json: str, compressed_lines: list[dict]) -> dict:
    """
    COMPRESSOR STAGE 1 TOOL. Validates and saves compressed lines for one chunk.
    compressed_lines must have EXACTLY the same count and line_numbers as original_json.
    If validation fails, falls back to original lines (uncompressed).
    Saves to COMPRESSED_DIR/chunk_NNN_compressed.log and .json
    Returns: {"result_log": "...", "result_json": "...", "compressed": bool}
    """
    with open(original_json, "r", encoding="utf-8") as f:
        original_data = json.load(f)
    original_lines = original_data.get("matches", [])

    if validate_compression(original_lines, compressed_lines):
        lines_to_save = compressed_lines
        compressed = True
    else:
        agent_logger.warning(
            f"[save_compressed_chunk] validation failed original={len(original_lines)} "
            f"compressed={len(compressed_lines)} — falling back to original"
        )
        lines_to_save = original_lines
        compressed = False

    chunk_name = Path(original_json).stem + "_compressed"
    output_base = str(Path(COMPRESSED_DIR) / chunk_name)
    paths = _save_results(output_base, lines_to_save)

    agent_logger.info(f"[save_compressed_chunk] chunk={original_json} compressed={compressed}")
    return {**paths, "compressed": compressed}


@tool
def merge_compressed_chunks() -> dict:
    """
    COMPRESSOR STAGE 2 TOOL. Merges all *_compressed.json files from COMPRESSED_DIR
    into a single list of lines preserving line_number references to failure.log.
    Returns: {"merged_lines": [...], "total_lines": int}
    """
    chunk_files = read_json_files(COMPRESSED_DIR, pattern="*_compressed.json")
    merged_lines = []
    for chunk in chunk_files:
        merged_lines.extend(chunk["data"].get("matches", []))

    agent_logger.info(f"[merge_compressed_chunks] files={len(chunk_files)} total_lines={len(merged_lines)}")
    return {"merged_lines": merged_lines, "total_lines": len(merged_lines)}


class SaveFinalReportInput(BaseModel):
    compressed_lines: list[dict] = Field(
        description='Final compressed list of {"line_number": int, "content": str}'
    )


@tool(args_schema=SaveFinalReportInput)
def save_final_report(compressed_lines: list[dict]) -> dict:
    """
    COMPRESSOR STAGE 2 TOOL. Saves final compressed report to COMPRESSED_DIR/final_report.log and .json.
    Call this after merge_compressed_chunks — with original merged_lines if within token budget,
    or with LLM-compressed lines if budget was exceeded.
    Returns: {"result_log": "...", "result_json": "..."}
    """
    output_base = str(Path(COMPRESSED_DIR) / "final_report")
    paths = _save_results(output_base, compressed_lines)
    agent_logger.info(f"[save_final_report] lines={len(compressed_lines)} output={output_base}")
    return paths