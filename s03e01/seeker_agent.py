from pathlib import Path
import sys
import os
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openrouter import ChatOpenRouter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from libs.loggers import agent_logger, LoggerCallbackHandler


AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL        = os.environ["SOLUTION_URL"]

DATA_FOLDER_PATH    = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH  = os.environ["PARENT_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]


from tools import describe_drone_map, drone_grid_split, extract_drone_documentation, get_file_list, html_to_markdown_tool, read_json, _RECURSION_LIMIT, save_file_from_url, save_json, scan_flag, send_drone_instructions

seeker_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "seeker_system.md"
                     ).read_text(encoding="utf-8")

SEEKER_CONFIG = {
    "configurable": {"thread_id": "s03e01-seeker"},
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": _RECURSION_LIMIT,
}

seeker_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
)

seeker = create_agent(
    model=seeker_model,
    tools=[

    ],
    system_prompt=seeker_system,
    name="seeker",
    checkpointer=InMemorySaver(),
)
