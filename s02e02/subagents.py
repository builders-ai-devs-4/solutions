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
import re

from modules.optimise_countur import check_edge_connectivity, check_edge_connectivity, edges_to_char, preprocess_cell


prompt_logger = get_logger("prompt", log_dir=_log_dir(), log_stem="prompt")

MAX_TOOL_ITERATIONS = 10  # 10 requests + reset + download CSV ~ 12 tool calls
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 22 + 2  # 222

MAP_URL = os.environ["MAP_URL"]
MAP_RESET_URL = os.environ["MAP_RESET_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]

char_classify_prompt = (Path(PARENT_FOLDER_PATH) / "prompts" / "char_classify_prompt.md"
                     ).read_text(encoding="utf-8")
VALID_CHARS = set("│─└┘┌┐├┤┬┴┼")
# _classify_llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=10, temperature=0)
# _classify_llm = ChatOpenAI(model="gpt-5-mini", max_tokens=500, temperature=0)
# _classify_llm = ChatOpenAI(model="gpt-5-mini", temperature=0)
# _classify_llm = ChatOpenAI(model="gpt-5", temperature=0)
_classify_llm = ChatOpenAI(model="gpt-5-mini", temperature=0)

def classify_cell(image_path: str) -> str:
    # W pełni odcinamy modele OpenAI dla tego zadania.
    image_path = Path(image_path)
    
    try:
        # 1. Przygotowujemy obrazek (biała, solidna rura na czarnym tle)
        img = preprocess_cell(str(image_path))
        
        # 2. Sprawdzamy matematycznie, w które ściany uderza biel
        edges = check_edge_connectivity(img)
        
        # 3. Tłumaczymy to na znak z Twojego słownika
        char = edges_to_char(edges)
        
        agent_logger.info(f"[classify_cell] {image_path.name} -> edges={edges} char='{char}'")
        return char
        
    except Exception as e:
        agent_logger.error(f"[classify_cell] Failed local CV processing for {image_path.name}: {e}")
        return "?"
    
def classify_cell_llm(image_path: str) -> str:
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

    if not result:
        agent_logger.warning(f"[classify_cell] {image_path.name} -> EMPTY response")
        return "?"

    match = re.search(r'<char>(.)</char>', result)
    if match and match.group(1) in VALID_CHARS:
        char = match.group(1)
    else:
        # Fallback: znajdź jakikolwiek prawidłowy znak w całej odpowiedzi
        valid_found = [c for c in result if c in VALID_CHARS]
        char = valid_found[-1] if valid_found else None
    
    if char is None:
        agent_logger.warning(
            f"[classify_cell] {image_path.name} -> UNKNOWN raw='{result}' "
            f"— cell could not be classified"
        )
        return "?"  # jawny sygnał błędu, agent może go wykryć w promptcie
    
    agent_logger.info(f"[classify_cell] {image_path.name} -> raw='{result}' char='{char}'")
    return char


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

    agent_logger.info(f"[classify_grid] cells_dir={cells_dir} n_rows={n_rows} n_cols={n_cols}")
    grid = [
        [classify_cell(str(coords[(r, c)])) for c in range(1, n_cols + 1)]
        for r in range(1, n_rows + 1)
    ]

    unknown = [
        f"{r}x{c}={grid[r-1][c-1]}"
        for r in range(1, n_rows + 1)
        for c in range(1, n_cols + 1)
        if grid[r-1][c-1] == "?"
    ]
    if unknown:
        agent_logger.warning(f"[classify_grid] unclassified cells: {unknown}")

    return grid
