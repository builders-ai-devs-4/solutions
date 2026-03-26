from pathlib import Path
import re
import sys
from typing import Optional
from langchain_core.tools import tool
import os
import requests
from modules.tiktoken import encode_prompt
from datetime import datetime, date
# from modules.models import SolutionUrlRequest, AnswerModel
from modules.drone_grid_splitter import detect_grid, get_row_col_lines, read_image
from s02e05.modules.drone_model import CellCoord, CellCoord, DroneGridInput, DroneGridOutput


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

DRONE_MAP_URL = os.getenv('DRONE_MAP_URL')

MAILBOX_MESSAGES_DIR = os.environ["MAILBOX_MESSAGES_DIR"]
MAILBOX_HELP_DIR = os.environ["MAILBOX_HELP_DIR"]
HELP_FILE_NAME = os.environ["HELP_FILE_NAME"]


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
    img_path   = Path(image_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    img_bgr = read_image(image_path)  # Validate that the image can be read before proceeding
    row_lines, col_lines = get_row_col_lines(image_path)
    
    n_rows = len(row_lines) - 1
    n_cols = len(col_lines) - 1
    
    raw_cells  = cut_cells(img_bgr, row_lines, col_lines)
    meta_table = save_cells(raw_cells, output_dir, prefix="cell")
    
    vis_path = output_dir / "visualization.png"
    save_visualization(img_bgr, row_lines, col_lines, vis_path)
    save_csv(meta_table, output_dir / "cells.csv")

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
    )

    return result