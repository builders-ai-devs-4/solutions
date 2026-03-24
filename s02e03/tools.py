from pathlib import Path
import re
import sys
from typing import Literal, Optional, Tuple
from langchain_core.tools import tool
import os
from langchain_openrouter import ChatOpenRouter
from pydantic import BaseModel, Field
import requests
from langchain_core.callbacks import BaseCallbackHandler
from modules.tiktoken import encode_prompt
from modules.models import AnswerModel, SolutionUrlRequest
from datetime import datetime, date


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from log_filters import _load_lines, _save_results, chunk_by_time_window, keyword_search, severity_filter, validate_compression

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
    
    """
    Download a file from a URL and save it to the specified folder.
    Returns the path to the saved file.

    prefix → '{prefix}_{stem}{ext}',  e.g. prefix='backup' → 'backup_failure.log'
    suffix → '{stem}_{suffix}{ext}',  e.g. suffix='2026-03-23' → 'failure_2026-03-23.log'

    Do NOT include underscore or extension in suffix/prefix — added automatically.
    """
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
    line references back to the original failure.log.
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
    Passing .json is significantly faster and preserves line references to failure.log.
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
    file_path: str = Field(description="Path to .log file or .json from severity_log_filter")

WINDOW_MINUTES: int = 60

@tool(args_schema=ChunkByTimeWindowInput)
def chunk_log_by_time(
    file_path: str,
    ) -> dict:
    """
    PRE-PROCESSING TOOL. Splits a log file into fixed-size time chunks chunk_NNN.json
    saved to CHUNKS_DIR. Use this BEFORE sending logs to the Compressor.
    Returns a list of chunk file paths: {"chunks": [{"chunk_index": 1, "result_json": "..."}, ...]}
    """
    window_minutes = WINDOW_MINUTES
    result = chunk_by_time_window(
        file_path=file_path,
        output_dir=str(CHUNKS_DIR),
        window_minutes=window_minutes,
    )
    agent_logger.info(
        f"[chunk_log_by_time] file={file_path} window={window_minutes}min chunks={len(result.get('chunks', []))}"
    )
    return result

# class SaveCompressedChunkInput(BaseModel):
#     original_json: str = Field(
#         description="Path to original chunk_NNN.json (from chunk_log_by_time)"
#     )
#     compressed_lines: list[dict] = Field(
#         description=(
#             "The compressed output YOU generated for this chunk. "
#             "Each entry: {\"line\": int, \"content\": str}. "
#             "You MUST provide this — do NOT call this tool without it. "
#             "line values must match line numbers from original_json."
#         )
#     )

def _save_compressed_chunk(
    original_json: str,
    compressed_lines: list[dict] | None = None
) -> dict:
    
    chunk_name = Path(original_json).stem + "_compressed"
    output_base = str(Path(COMPRESSED_DIR) / chunk_name)
    output_json = Path(output_base).with_suffix(".json")

    if output_json.exists():
        agent_logger.info(f"[save_compressed_chunk] already exists, skipping: {output_json}")
        return {"result_json": str(output_json), "compressed": True}

    if not compressed_lines:
        raise ValueError(
            "compressed_lines is required and must be non-empty. "
            "Call read_file first, compress lines in memory, then call this tool."
        )

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

    paths = _save_results(output_base, lines_to_save)
    agent_logger.info(f"[save_compressed_chunk] chunk={original_json} compressed={compressed}")
    return {**paths, "compressed": compressed}

@tool
def save_compressed_chunk(
    original_json: str,
    compressed_lines: list[dict] | None = None
) -> dict:
    """
    COMPRESSOR STAGE 1 TOOL.
    CALL SEQUENCE (STRICT):
      1. read_file(chunk_path)         ← read first
      2. compress lines in memory      ← compress second
      3. save_compressed_chunk(...)    ← save third — NEVER before step 2

    compressed_lines MUST be a non-empty list — unless chunk already exists
    in COMPRESSED_DIR (then it is skipped automatically).
    original_json MUST be a .json file from CHUNKS_DIR, NOT a .log file.
    """
    return _save_compressed_chunk(original_json=original_json, compressed_lines=compressed_lines)


@tool
def merge_compressed_chunks() -> str:
    """
    COMPRESSOR STAGE 2 TOOL. Merges all chunk_*_compressed.json files from
    COMPRESSED_DIR into a single list sorted by line number.
    Saves merged_compressed.json to COMPRESSED_DIR.
    Call save_final_report after this tool.
    Returns path to merged_compressed.json.
    """
    chunk_files = read_json_files(COMPRESSED_DIR, pattern="chunk_*_compressed.json")
    merged_lines = []

    for chunk in chunk_files:
        merged_lines.extend(chunk["data"]["matches"]) # flat lista po zmianie _save_results

    merged_lines.sort(key=lambda e: e["line"])

    output_base = str(Path(COMPRESSED_DIR) / "merged_compressed")
    _save_results(output_base, merged_lines)  # zapisuje {"matches": [...]}

    output_path = Path(output_base).with_suffix(".json")
    agent_logger.info(f"[merge_compressed_chunks] files={len(chunk_files)} total={len(merged_lines)}")
    return str(output_path)

@tool
def save_final_report() -> str:
    """
    COMPRESSOR STAGE 3 TOOL. Reads merged_compressed.json from COMPRESSED_DIR,
    flattens all 'content' fields to plain text and saves as final_report.log
    and final_report.json.
    Call this after merge_compressed_chunks — no parameters needed.
    This is the LAST step — do not compress further after this without token check.
    Returns path to final_report.log.
    """
    merged_path = Path(COMPRESSED_DIR) / "merged_compressed.json"
    merged_lines = _load_lines(str(merged_path))

    output_base = str(Path(COMPRESSED_DIR) / "final_report")
    paths = _save_results(output_base, merged_lines)

    agent_logger.info(f"[save_final_report] lines={len(merged_lines)} output={output_base}")
    return paths["result_log"]


class InjectKeywordsIntoMergeInput(BaseModel):
    merge_path: str = Field(...)
    keywords_compressed_path: str = Field(...)
    output_path: str = Field(...)
    overwrite: bool = Field(
        default=False,
        description=(
            "If True, existing entries with the same line number will be "
            "replaced by the new version. Use when recovering over-compressed lines."
        )
    )

@tool(args_schema=InjectKeywordsIntoMergeInput)
def inject_keywords_into_merge(
    merge_path: str,
    keywords_compressed_path: str,
    output_path: str,
    overwrite: bool = False,
) -> str:
    
    """
    Injects new compressed keyword lines into an existing merged_compressed.json.
    overwrite=False: skip duplicate line numbers (new component).
    overwrite=True: replace existing entries with same line number (recover detail).
    Returns output_path.
    """
    
    merge_lines: list[dict] = json.loads(Path(merge_path).read_text(encoding="utf-8"))
    kw_lines: list[dict] = json.loads(Path(keywords_compressed_path).read_text(encoding="utf-8"))

    if overwrite:
        kw_by_line = {e["line"]: e for e in kw_lines}
        result = [kw_by_line.get(e["line"], e) for e in merge_lines]
        new_lines = [e for e in kw_lines if e["line"] not in {x["line"] for x in merge_lines}]
        result.extend(new_lines)
    else:
        existing_lines: set[int] = {e["line"] for e in merge_lines}
        result = merge_lines[:]
        for entry in kw_lines:
            if entry["line"] not in existing_lines:
                result.append(entry)
                existing_lines.add(entry["line"])

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    agent_logger.info(
        f"[inject_keywords_into_merge] overwrite={overwrite} out={output_path}"
    )
    return output_path


class SortMergeByLineNumberInput(BaseModel):
    merge_path: str = Field(
        description=(
            "Path to a merged JSON file containing an 'entries' list "
            "with {line, compressed} objects."
        )
    )
    output_path: str = Field(
        description=(
            "Path where the sorted JSON will be saved. "
            "Can be the same as merge_path to sort in place."
        )
    )

@tool(args_schema=SortMergeByLineNumberInput)
def sort_merge_by_line_number(
    merge_path: str,
    output_path: str,
) -> str:
    
    """
    Sorts entries in a merged_compressed.json by line number ascending.
    Call this after inject_keywords_into_merge to restore chronological order.
    Returns output_path.
    """
    
    lines: list[dict] = json.loads(Path(merge_path).read_text(encoding="utf-8"))

    lines.sort(key=lambda e: e["line"])

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(
        json.dumps(lines, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    agent_logger.info(f"[sort_merge_by_line_number] out={output_path}")
    return output_path

# @tool
# def save_recompressed_final(compressed_lines: list[dict]) -> str:
#     """
#     COMPRESSOR STAGE 3b TOOL. Use when count_prompt_tokens on final_report.log
#     exceeds TOKEN_LIMIT. Overwrites final_report.log and final_report.json.

#     REPEAT until within TOKEN_LIMIT:
#       1. read_file(final_report.json)          — structured data with line numbers
#       2. Shorten lines — keep CRIT, compress WARN/ERRO aggressively, drop duplicates
#       3. save_recompressed_final(shortened_lines)
#       4. count_prompt_tokens(final_report.log) — if still over, go to step 1

#     Returns path to final_report.log (pass this to Supervisor when done).
#     """
#     output_base = str(Path(COMPRESSED_DIR) / "final_report")
#     paths = _save_results(output_base, compressed_lines)
#     agent_logger.info(f"[save_recompressed_final] lines={len(compressed_lines)}")
#     return paths["result_log"]

@tool
def recompress_final() -> str:
    """
    COMPRESSOR STAGE 3b TOOL. Use when count_prompt_tokens on final_report.log
    exceeds TOKEN_LIMIT. Reads final_report.json, re-compresses using LLM,
    overwrites final_report.log and final_report.json.

    REPEAT until within TOKEN_LIMIT:
      1. recompress_final() — returns path to final_report.log
      2. count_prompt_tokens(read_file(final_report.log))
      3. If still over → go to step 1

    Returns path to final_report.log.
    """
    
    lines = _load_lines(str(Path(COMPRESSED_DIR) / "final_report.json"))
    compressed_lines = _compress_lines(lines)

    output_base = str(Path(COMPRESSED_DIR) / "final_report")
    paths = _save_results(output_base, compressed_lines)

    agent_logger.info(f"[recompress_final] lines={len(compressed_lines)}")
    return paths["result_log"]



compression_model = ChatOpenRouter(
    model="google/gemini-3-flash-preview",
    temperature=0,
)

def _compress_lines(lines: list[dict]) -> list[dict]:
    """
    Compresses a list of log lines using LLM.
    Returns compressed list or original on failure.
    """
    prompt = f"""Compress each log line to this exact format:
YYYY-MM-DD HH:MM [LEVEL] [COMPONENT] Short one-sentence description.

Rules:
- Extract component ID (e.g. ECCS8, WTANK07) into its own bracket
- Remove seconds from timestamp
- Keep ALL lines — one output entry per input line
- Return ONLY a JSON array, no markdown, no explanation:
[{{"line": <original_line_number>, "content": "<compressed line>"}}]

Input:
{json.dumps(lines, ensure_ascii=False)}"""

    response = compression_model.invoke(prompt)

    try:
        compressed = json.loads(response.content)
    except json.JSONDecodeError:
        agent_logger.warning(f"[_compress_lines] JSON decode error — falling back to original")
        return lines

    if not validate_compression(lines, compressed):
        agent_logger.warning(f"[_compress_lines] validation failed "
                             f"original={len(lines)} compressed={len(compressed)} "
                             f"— falling back to original")
        return lines

    return compressed

@tool
def compress_chunk(chunk_path: str) -> str:
    """
    COMPRESSOR STAGE 1 TOOL. Reads a chunk .json, compresses all lines using LLM,
    saves result to COMPRESSED_DIR. Use this for every chunk — ONE BY ONE.
    Skips saving if chunk_NNN_compressed.json already exists in COMPRESSED_DIR.
    Returns path to chunk_NNN_compressed.json.

    Args:
        chunk_path: Path to chunk_NNN.json from CHUNKS_DIR.
    """
    lines = _load_lines(chunk_path)
    compressed_lines = _compress_lines(lines)
    result = _save_compressed_chunk(chunk_path, compressed_lines)
    return result["result_json"]
