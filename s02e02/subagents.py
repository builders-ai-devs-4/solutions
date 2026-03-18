import os
from pathlib import Path
import langchain
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from libs.filetype_detect import detect_file_type
from libs.generic_helpers import read_file_base64
from loggers import LoggerCallbackHandler, agent_logger,get_logger, _log_dir
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.output_parsers import StrOutputParser
from langchain.messages import SystemMessage, HumanMessage

prompt_logger = get_logger("prompt", log_dir=_log_dir(), log_stem="prompt")

MAX_TOOL_ITERATIONS = 10  # 10 requests + reset + download CSV ~ 12 tool calls
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 12 + 2  # 122

MAP_URL = os.environ["MAP_URL"]
MAP_RESET_URL = os.environ["MAP_RESET_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]

char_classify_prompt = (Path(PARENT_FOLDER_PATH) / "prompts" / "char_classify_prompt.md"
                     ).read_text(encoding="utf-8")
VALID_CHARS = set("│─└┘┌┐├┤┬┴┼ ")
_classify_llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=5, temperature=0)


def classify_cell(image_path: str) -> str:
    # Returns one Unicode box-drawing char for the given cell image.
    image_path = Path(image_path)
    b64 = read_file_base64(image_path)
    media_type = detect_file_type(image_path).mime_from_name

    message = HumanMessage(content=[
        {"type": "text", "text": char_classify_prompt},
        {"type": "image_url", "image_url": {
            "url": f"data:{media_type};base64,{b64}",
            "detail": "low",
        }},
    ])

    result = (_classify_llm | StrOutputParser()).invoke([message]).strip()
    return result[0] if result and result[0] in VALID_CHARS else " "


@tool("classify_grid", description=(
    "Classifies all cells of the wiring diagram grid. "
    "Input: path to directory containing cell_{row}_{col}.png images. "
    "Returns 2D list of Unicode box-drawing characters."
))
def classify_grid(cells_dir: str) -> list[list[str]]:
    """Classify grid cells from a directory of cell_{row}_{col}.png images.

    Args:
        cells_dir: Directory containing cell images from the grid splitter.

    Returns:
        2D list of Unicode characters indexed by [row][col].
    """
    cells_dir = Path(cells_dir)

    # Parse all cell_R_C.png files and find grid dimensions
    coords: dict[tuple[int, int], Path] = {}
    for p in cells_dir.glob("cell_*.png"):
        _, r, c = p.stem.split("_")
        coords[(int(r), int(c))] = p

    if not coords:
        raise ValueError(f"No cell images found in: {cells_dir}")

    n_rows = max(r for r, _ in coords) 
    n_cols = max(c for _, c in coords)

    return [
        [classify_cell(str(coords[(r, c)])) for c in range(1, n_cols + 1)]
        for r in range(1, n_rows + 1)
    ]
    
