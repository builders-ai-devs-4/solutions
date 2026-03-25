from pathlib import Path
import sys
import os
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools import get_file_list, get_help_from_mailbox, post_action_to_mailbox, read_json, _RECURSION_LIMIT, save_json, scan_flag, submit_solution

from loggers import LoggerCallbackHandler, agent_logger
from langchain_openrouter import ChatOpenRouter

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL        = os.environ["SOLUTION_URL"]

DATA_FOLDER_PATH    = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH  = os.environ["PARENT_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
MAILBOX_URL = os.getenv('MAILBOX_URL')

MAILBOX_MESSAGES_DIR = os.environ["MAILBOX_MESSAGES_DIR"]
MAILBOX_HELP_DIR = os.environ["MAILBOX_HELP_DIR"]
HELP_FILE_NAME = os.environ["HELP_FILE_NAME"]


seeker_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "seeker_system.md"
                     ).read_text(encoding="utf-8")

SEEKER_CONFIG = {
    "configurable": {"thread_id": "s02e04-seeker"},
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
        get_help_from_mailbox,
        get_file_list,
        post_action_to_mailbox,
        submit_solution,
        read_json,
        scan_flag,
        save_json
    ],
    system_prompt=seeker_system,
    name="seeker",
    checkpointer=InMemorySaver(),
)
