import os
from pathlib import Path
import langchain
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from libs.filetype_detect import detect_file_type
from libs.generic_helpers import read_file_base64
from tools import detect_mimetype, read_file, read_csv, save_file_from_url, scan_flag, send_to_server, count_prompt_tokens
from loggers import LoggerCallbackHandler, agent_logger,get_logger, _log_dir
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.output_parsers import StrOutputParser
from langchain.messages import SystemMessage, HumanMessage

prompt_logger = get_logger("prompt", log_dir=_log_dir(), log_stem="prompt")

MAX_TOOL_ITERATIONS = 10  # 10 requests + reset + download CSV ~ 12 tool calls
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 12 + 2  # 122

MAP_URL = os.environ["MAP_URL"]
MAP_RESET_URL = os.environ["MAP_RESET_URL"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]

char_classify_prompt = (Path(PARENT_FOLDER_PATH) / "prompts" / "vision_interpreter_system.md"
                     ).read_text(encoding="utf-8")

VISION_INTERPRETER_CONFIG = {
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": _RECURSION_LIMIT,
}



_vision_interpreter = create_agent(
    model="openai:gpt-5.1",

    tools=[detect_mimetype, read_file ],
    system_prompt=char_classify_prompt,
    name="vision_interpreter",
)

@tool("vision_interpreter", description=(
    "Interprets a wiring diagram cell image and classifies it into a Unicode box-drawing character."))
def call_vision_interpreter(task: str) -> str:
    result = _vision_interpreter.invoke(
        {"messages": [{"role": "user", "content": task}]},
        config=VISION_INTERPRETER_CONFIG,
    )
    answer = result["messages"][-1].content
    agent_logger.info(f"[vision_interpreter] {answer}")
    prompt_logger.info(answer)
    return answer

def classify_cell(image_path: str) -> str:
    """Classify a single wiring diagram cell image into a Unicode box-drawing character.

    Sends the image to the OpenAI vision model with a structured prompt and
    few-shot examples. Uses temperature=0 for deterministic output and
    max_tokens=5 to physically prevent the model from generating any
    explanation beyond the single character.

    Args:
        image_path: Path to the cell image file.

    Returns:
        A single Unicode character from VALID_CHARS, or a space if the
        cell is empty or the model returned an unexpected value.
    """
    llm = ChatOpenAI(
        model="gpt-5-mini",
        max_tokens=5,   # single char = 1 token; hard limit prevents any explanation
        temperature=0,  # deterministic — same image always returns same result
    )
    
    VALID_CHARS = set("│─└┘┌┐├┤┬┴┼ ")
    image_path = Path(image_path)
    b64 = read_file_base64(image_path)
    media_type = (detect_file_type(image_path)).mime_from_name

    message = HumanMessage(
        content=[
            {"type": "text", "text": char_classify_prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{b64}",
                    "detail": "low",  # sufficient for small tiles, saves ~75% image tokens
                },
            },
        ]
    )

    chain = llm | StrOutputParser()
    result = chain.invoke([message]).strip()

    if result and result[0] in VALID_CHARS:
        return result[0]
    return " "


def classify_grid(
    cell_paths: list[list[str]],
) -> list[list[str]]:
    """Classify all cells in a 2D grid of wiring diagram images.

    Processes cells row by row, left to right. For large grids consider
    switching to an async implementation to parallelize API calls.

    Args:
        cell_paths: 2D list of file paths, where cell_paths[row][col]
            points to the image for that grid position.

    Returns:
        2D list of Unicode characters mirroring the shape of cell_paths.

    Example:
        grid = classify_grid([
            ["cell_0_0.jpg", "cell_0_1.jpg"],
            ["cell_1_0.jpg", "cell_1_1.jpg"],
        ])
        # grid → [['┌', '─'], ['│', ' ']]
    """
    return [
        [classify_cell(path) for path in row]
        for row in cell_paths
    ]
