import os
import sys
from pathlib import Path

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openrouter import ChatOpenRouter
from langfuse.langchain import CallbackHandler

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

AI_DEVS_SECRET = os.environ["AI_DEVS_SECRET"]
TASK_NAME = os.environ["TASK_NAME"]
SOLUTION_URL = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
DB_PATH = Path(os.environ["DB_PATH"])
DB_RUNTIME_PATH = Path(os.environ["DB_RUNTIME_PATH"])

from libs.loggers import LoggerCallbackHandler, agent_logger

from subagents import (
    run_recon_agent_tool,
    run_demand_agent_tool,
    run_mapping_agent_tool,
    run_identity_agent_tool,
    run_planner_agent_tool,
    run_executor_agent_tool,
    run_auditor_agent_tool,
)

from tools import (
    _RECURSION_LIMIT,
    api_done,
    api_reset,
    scan_flag,
)

langfuse_handler = CallbackHandler()

supervisor_prompt_path = Path(PARENT_FOLDER_PATH) / "prompts" / "supervisor_system.md"
supervisor_system = supervisor_prompt_path.read_text(encoding="utf-8")

SUPERVISOR_CONFIG = {
    "configurable": {"thread_id": "supervisor-foodwarehouse"},
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
        run_recon_agent_tool,
        run_demand_agent_tool,
        run_mapping_agent_tool,
        run_identity_agent_tool,
        run_planner_agent_tool,
        run_executor_agent_tool,
        run_auditor_agent_tool,
        api_reset,
        api_done,
        scan_flag,
    ],
    system_prompt=supervisor_system,
    name="supervisor",
    checkpointer=InMemorySaver(),
)