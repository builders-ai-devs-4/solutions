import os
import sys
from pathlib import Path
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openrouter import ChatOpenRouter
from langfuse.langchain import CallbackHandler

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]

from libs.loggers import LoggerCallbackHandler, agent_logger

from subagents import run_explorer_cities_tool, run_explorer_goods_tool, run_explorer_persons_tool 
from tools import _RECURSION_LIMIT, fs_send, get_help_cache, normalize_city, normalize_item, scan_flag, validate_all


langfuse_handler = CallbackHandler()

supervisor_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "supervisor_system.md").read_text(encoding="utf-8")

SUPERVISOR_CONFIG = {
    "configurable": {"thread_id": "supervisor-savethem"},
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": _RECURSION_LIMIT,
}

supervisor_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
    model_kwargs={"parallel_tool_calls": False},
)


supervisor = create_agent(
    model=supervisor_model,
    tools=[
        run_explorer_cities_tool,
        run_explorer_persons_tool,
        run_explorer_goods_tool,
        normalize_city,
        normalize_item,
        validate_all,
        fs_send,
        scan_flag,
        get_help_cache
        
    ],
    system_prompt=supervisor_system,
    name="supervisor",
    checkpointer=InMemorySaver(),
)