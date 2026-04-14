import os
from pathlib import Path
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from subagents import _RECURSION_LIMIT, classify_grid
from tools import apply_rotation_to_grid, detect_mimetype, detect_mimetype, get_failed_plans, get_file_list, get_filename, get_grid_cells_frome_image, read_file, remember_failed_plan, reset_map, rotate_cell, save_file_from_url, scan_flag, count_prompt_tokens
from loggers import LoggerCallbackHandler, agent_logger,get_logger, _log_dir
from langchain_core.callbacks import BaseCallbackHandler

prompt_logger = get_logger("prompt", log_dir=_log_dir(), log_stem="prompt")

MAP_URL = os.environ["MAP_URL"]
MAP_RESET_URL = os.environ["MAP_RESET_URL"]
TASK_DATA_FOLDER_PATH   = os.environ["TASK_DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]

SUPERVISOR_SYS_PROMPT = (Path(PARENT_FOLDER_PATH) / "prompts" / "supervisor_system.md"
                     ).read_text(encoding="utf-8")

SUPERVISOR_CONFIG = {
    "configurable": {"thread_id": "s02e01-supervisor"},
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": _RECURSION_LIMIT,
}

supervisor = create_agent(
    model="openai:gpt-5-mini",
    tools=[
        classify_grid,
        scan_flag,
        save_file_from_url,
        rotate_cell,
        reset_map,
        get_file_list,
        read_file,
        detect_mimetype,
        get_grid_cells_frome_image,
        get_filename,
        apply_rotation_to_grid,
        get_failed_plans,
        remember_failed_plan
    ],
    system_prompt=SUPERVISOR_SYS_PROMPT,
    name="supervisor",
    checkpointer=InMemorySaver(),
)
