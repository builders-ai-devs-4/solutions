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
OKO_URL     = os.getenv('OKO_URL')

from libs.loggers import LoggerCallbackHandler, agent_logger

from subagents import call_explorer, call_planner
from tools import _RECURSION_LIMIT


langfuse_handler = CallbackHandler()

supervisor_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "supervisor_system.md").read_text(encoding="utf-8")

SUPERVISOR_CONFIG = {
    "configurable": {"thread_id": "supervisor-savethem"},
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": _RECURSION_LIMIT,
}

supervisor_model = ChatOpenRouter(
    model="openai/gpt-4o",
    temperature=0,
)


supervisor = create_agent(
    model=supervisor_model,
    tools=[
        call_explorer,
        call_planner
    ],
    system_prompt=supervisor_system,
    name="supervisor",
    checkpointer=InMemorySaver(),
)