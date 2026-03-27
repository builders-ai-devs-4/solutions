from pathlib import Path
import re
import sys
from typing import Optional
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
import os
from langchain_openrouter import ChatOpenRouter
from langchain.messages import SystemMessage, HumanMessage
import requests
from modules.tiktoken import encode_prompt
from datetime import datetime, date
# from modules.models import SolutionUrlRequest, AnswerModel
from modules.drone_grid_splitter import detect_grid, get_row_col_lines, read_image
from modules.models import CellCoord, CellCoord, CellDescription, DescribeDroneMapInput, DroneDocumentation, DroneDocumentation, DroneGridInput, DroneGridOutput, DroneInstructionsInput, HtmlToMarkdownInput, HtmlToMarkdownOutput, MapDescriptionOutput
from modules.tomarkdown import transform_html_to_markdown


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from libs.filetype_detect import detect_file_type
from libs.generic_helpers import get_filename_from_url, read_file_base64, read_file_text, save_file, save_json_file
from modules.grid_utils import cut_cells, save_cells, save_visualization, save_csv
from libs.loggers import agent_logger
import json

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL        = os.environ["SOLUTION_URL"]

DATA_FOLDER_PATH    = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH  = os.environ["PARENT_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]

MAP_FOLDER_PATH = os.environ["MAP_FOLDER_PATH"]
DOCS_FOLDER_PATH = os.environ["DOCS_FOLDER_PATH"]
DRONE_MAP_URL = os.getenv('DRONE_MAP_URL')
PWR_ID_CODE = os.getenv('PWR_ID_CODE')

FLAG_RE = re.compile(r"\{FLG:[^}]+\}")
MAX_TOOL_ITERATIONS = 10 
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 10 + 2  # 102

@tool(args_schema=DroneGridInput, response_format="content_and_artifact")
def drone_grid_split(image_path: str, output_dir: str = "output") -> tuple[str, DroneGridOutput]:
    """Splits a drone aerial photo with a red grid overlay into individual
    cell images.

    Returns a tuple of (content, artifact):
    - content  : JSON string consumed by the LLM — contains cell paths,
                 per-cell grid coordinates, and the grid visualisation path.
    - artifact : DroneGridOutput Pydantic model — full structured result
                 available to downstream code via ToolMessage.artifact.

    Use this tool when you need to extract and index rectangular regions
    from a drone photograph that has a visible red grid drawn on it.
    """
    image_path   = Path(image_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    img_bgr = read_image(image_path)  # Validate that the image can be read before proceeding
    row_lines, col_lines = get_row_col_lines(image_path)
    
    n_rows = len(row_lines) - 1
    n_cols = len(col_lines) - 1
    agent_logger.info(f"[drone_grid_split] image_path={image_path} n_rows={n_rows} n_cols={n_cols}")
    
    raw_cells  = cut_cells(img_bgr, row_lines, col_lines)
    meta_table = save_cells(raw_cells, output_dir, prefix="cell")
    
    vis_path = output_dir / "visualization.png"
    save_visualization(img_bgr, row_lines, col_lines, vis_path)
    save_csv(meta_table, output_dir / "cells.csv")
    agent_logger.info(f"[drone_grid_split] vis_path={vis_path} meta_table_rows={len(meta_table)}")

    cells_dir   = output_dir / "cells"
    cell_files  : list[str]       = []
    cell_coords : list[CellCoord] = []

    for r in range(n_rows):
        for c in range(n_cols):
            row_idx, col_idx = r + 1, c + 1
            cell_files.append(str(cells_dir / f"cell_{row_idx}x{col_idx}.png"))
            cell_coords.append(CellCoord(
                index  = f"{row_idx}x{col_idx}",
                cell_x = col_idx,
                cell_y = row_idx,
            ))

    result = DroneGridOutput(
        cells_dir          = str(cells_dir),
        cell_files         = cell_files,
        cell_coords        = cell_coords,
        grid_visualization = str(vis_path),
        n_rows             = n_rows,
        n_cols             = n_cols,
        drone_view_map_path = str(image_path),
    )

    return result.model_dump_json(indent=2), result


@tool(args_schema=HtmlToMarkdownInput, response_format="content_and_artifact")
def html_to_markdown_tool(html_url: str, output_dir: str = "output") -> tuple[str, HtmlToMarkdownOutput]:
    """Downloads an HTML page from a URL, converts it to clean Markdown,
    and saves the result to disk.

    Returns a tuple of (content, artifact):
    - content  : JSON string consumed by the LLM — contains the path to the
                 saved Markdown file, its filename, and the source URL.
    - artifact : HtmlToMarkdownOutput Pydantic model — full structured result
                 available to downstream code via ToolMessage.artifact.

    Use this tool when you need to fetch a web page and convert its content
    to Markdown for further processing, storage, or LLM consumption.
    """
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    markdown_file_path = transform_html_to_markdown(output_dir, html_url)

    result = HtmlToMarkdownOutput(
        markdown_file_path=str(markdown_file_path),
        filename=markdown_file_path.name,
        html_url=html_url
    )
    agent_logger.info(f"[html_to_markdown_tool] html_url={html_url} markdown_file_path={markdown_file_path}")
    
    return result.model_dump_json(indent=2), result

@tool
def extract_drone_documentation(md_path: str, output_json_path: str) -> str:
    """
    Use this tool to read raw drone API documentation from a Markdown file,
    fix its formatting using an LLM, and save it as a structured JSON file.
    Call this tool only when you know the Markdown file has been updated or needs initial parsing.
    """
    try:
        # Read the raw file
        with open(md_path, "r", encoding="utf-8") as file:
            raw_markdown = file.read()
            agent_logger.info(f"[extract_drone_documentation] md_path={md_path} raw_markdown_length={len(raw_markdown)}")
        # Initialize the extraction model (e.g., a cheaper/faster model for parsing)
        
        llm = ChatOpenRouter(
            model="openai/gpt-4o",
            temperature=0,
        )
        
        structured_llm = llm.with_structured_output(DroneDocumentation)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a data analysis expert. Analyze the raw API documentation.
            Fix inconsistencies, group the methods by their functional areas, and return a valid JSON.
            Do not invent new API functions."""),
            ("user", "Documentation:\n\n{documentation}")
        ])
        
        # Processing pipeline
        chain = prompt | structured_llm
        result = chain.invoke({"documentation": raw_markdown})
        
        # Save to JSON file
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
            agent_logger.info(f"[extract_drone_documentation] JSON content: {json.dumps(result.model_dump(), ensure_ascii=False, indent=2)}")
        agent_logger.info(f"[extract_drone_documentation] md_path={md_path} output_json_path={output_json_path}")
        
        return f"Success: Extracted data from {md_path} and saved to {output_json_path}."
        
    except FileNotFoundError:
        return f"Error: Source file {md_path} does not exist."
    except Exception as e:
        return f"An unexpected error occurred during extraction: {str(e)}"
    
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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_image_message(base64_data: str, prompt: str) -> HumanMessage:
    """Build a LangChain HumanMessage with an inline base64 image."""
    return HumanMessage(content=[
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{base64_data}"},
        },
        {
            "type": "text",
            "text": prompt,
        },
    ])


def _parse_cell_index(filename: str) -> tuple[int, int]:
    """Extract (row, col) from a filename like 'cell_2x3.png'."""
    match = re.search(r"cell_(\d+)x(\d+)", filename)
    if not match:
        raise ValueError(f"Cannot parse cell index from filename: {filename}")
    return int(match.group(1)), int(match.group(2))


def _get_llm():
    """Initialise the vision-capable LLM (reads model from env or uses default)."""
    from langchain_openrouter import ChatOpenRouter
    model = os.getenv("VISION_MODEL", "openai/gpt-4o")
    return ChatOpenRouter(model=model, temperature=0)


# ---------------------------------------------------------------------------
# LangChain @tool
# ---------------------------------------------------------------------------

@tool(args_schema=DescribeDroneMapInput, response_format="content_and_artifact")
def describe_drone_map(
    drone_view_map_path: str,
    grid_visualization_path: str,
    cells_dir: str,
    output_json_path: str,
) -> tuple[str, MapDescriptionOutput]:
    """Describes a drone aerial photograph using a vision LLM.

    Step 0 — Overall description: sends original map image (not the visualization)
    to the vision model and asks for a high-level description of the entire
    map, including visible structures, terrain, and spatial cell layout.

    Step 1 — Overall description: sends the annotated grid visualization
    to the vision model and asks for a high-level description of the entire
    map, including visible structures, terrain, and spatial cell layout.

    Step 2 — Per-cell descriptions: iterates over all cell PNG files in
    ``cells_dir`` (sorted row-first by RxC index), sends each to the vision
    model, and collects a focused description of that cell's content.

    Step 3 — Saves the combined result to ``output_json_path`` as JSON.

    Returns a tuple of (content, artifact):
    - content  : JSON string for the LLM — overall description + cell list.
    - artifact : MapDescriptionOutput Pydantic model for downstream code,
                 accessible via ToolMessage.artifact.

    Use this tool after drone_grid_split has produced the visualization and
    cell images. Pass its output paths directly as input here.
    """
    llm = _get_llm()

    # ── Step 0: Overall map description ────────────────────────────────────
    agent_logger.info(f"[describe_drone_map] Reading map image: {drone_view_map_path}")
    map_b64 = read_file_base64(drone_view_map_path)

    map_prompt = (
        "This is a raw aerial drone photograph of a power plant terrain, WITHOUT any grid overlaid. "
        "Describe the entire scene comprehensively as a single continuous landscape. "
        "Focus on the layout of the main structures, natural terrain features, "
        "roads, vegetation, and water bodies. Use natural spatial references "
        "(e.g., 'in the upper left', 'towards the center', 'in the southern part'). "
        "CRITICAL: Do NOT attempt to divide the image into grid cells, rows, or columns, "
        "and do NOT use any coordinate numbers. "
        "There is a main dam located in this area. To help locate it, "
        "the water color near the dam has been intentionally intensified. "
        "Explicitly describe the general spatial area where this intensified water color is visible. "
        "This general description will serve as foundational context."
    )
    
    map_msg  = _build_image_message(map_b64, map_prompt)
    map_resp = llm.invoke([map_msg])
    map_description = map_resp.content
    agent_logger.info(f"[describe_drone_map] Map description length: {len(map_description)}")

    # ── Step 1: Overall map description ────────────────────────────────────
    agent_logger.info(f"[describe_drone_map] Reading visualization: {grid_visualization_path}")
    vis_b64 = read_file_base64(grid_visualization_path)

    overall_prompt = (
        "This is an aerial drone photograph of a power plant terrain divided into a labelled grid. "
        "Describe what you see on the entire map: the main structures, "
        "terrain features, and how the content is distributed across the grid cells. "
        "CRITICAL: You must definitively locate the main dam. The water color near the dam "
        "has been intentionally intensified to make it stand out. You MUST explicitly identify "
        "and state the exact grid cell containing the dam based on this visual cue. "
        "Be concise but thorough — this description will be used as context "
        "for a navigation agent."
    )
    overall_msg  = _build_image_message(vis_b64, overall_prompt)
    overall_resp = llm.invoke([overall_msg])
    overall_description = overall_resp.content
    agent_logger.info(f"[describe_drone_map] Overall description length: {len(overall_description)}")

    # ── Step 2: Per-cell descriptions ──────────────────────────────────────
    cells_path = Path(cells_dir)
    cell_files = sorted(
        [f for f in cells_path.glob("cell_*.png")],
        key=lambda f: _parse_cell_index(f.name),
    )
    agent_logger.info(f"[describe_drone_map] Found {len(cell_files)} cell files")

    cell_prompt = (
        "This is a single cell ({index}) cropped from a larger aerial drone photograph of a power plant. "
        "Describe only what is visible in this cell: structures, terrain, water, "
        "vegetation, objects. CRITICAL: We are looking for the main dam, indicated by "
        "intentionally intensified water color. If you observe this intensified water color "
        "or dam structures, you MUST explicitly state that this cell contains the dam. "
        "Be specific and concise."
    )

    cell_descriptions: list[CellDescription] = []
    for cell_file in cell_files:
        row_idx, col_idx = _parse_cell_index(cell_file.name)
        index = f"{row_idx}x{col_idx}"

        agent_logger.info(f"[describe_drone_map] Describing cell {index}")
        cell_b64  = read_file_base64(str(cell_file))
        cell_msg  = _build_image_message(
            cell_b64,
            cell_prompt.format(index=index),
        )
        cell_resp = llm.invoke([cell_msg])

        cell_descriptions.append(CellDescription(
            index       = index,
            cell_x      = col_idx,
            cell_y      = row_idx,
            description = cell_resp.content,
        ))

    # ── Step 3: Save to JSON ────────────────────────────────────────────────
    result = MapDescriptionOutput(
        overall_description = overall_description,
        cells               = cell_descriptions,
        output_json_path    = str(Path(output_json_path).resolve()),
        map_description     = map_description,
    )

    out_path = Path(output_json_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result.model_dump_json(indent=2))

    agent_logger.info(f"[describe_drone_map] Saved JSON: {output_json_path}")

    return result.model_dump_json(indent=2), result

@tool(args_schema=DroneInstructionsInput)
def send_drone_instructions(instructions: list[str]) -> str:
    """
    Sends a sequence of instructions to the drone's API hub.
    Use this to test commands, fly the drone, and execute the final mission.
    The API will return errors if your instructions are invalid or out of order.
    Read the returned errors carefully to adjust your next attempt.
    """
    url = SOLUTION_URL
    payload = {
        "apikey": AI_DEVS_SECRET,
        "task": TASK_NAME,
        "answer": {
            "instructions": instructions
        }
    }
    
    agent_logger.info(f"[send_drone_instructions] Sending {instructions} instructions to {url}")
    
    try:
        response = requests.post(url, json=payload)
        response_text = response.text
        agent_logger.info(f"[send_drone_instructions] Response: {response_text}")
  
        
        return response_text
    except Exception as e:
        error_msg = f"Failed to connect to the drone API: {str(e)}"
        agent_logger.error(error_msg)
        return error_msg
