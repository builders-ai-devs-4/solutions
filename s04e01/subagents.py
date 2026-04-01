from pathlib import Path
from string import Template
import sys
from langchain_core.tools import tool
import os
from langchain.agents import create_agent
from langchain_openrouter import ChatOpenRouter
from langgraph.checkpoint.memory import InMemorySaver
from langfuse.langchain import CallbackHandler

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
OKO_URL     = os.getenv('OKO_URL')

explorer_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "explorer_system.md").read_text(encoding="utf-8")
explorer_description_template = (Path(PARENT_FOLDER_PATH) / "prompts" / "explorer_description.md").read_text(encoding="utf-8")
explorer_description = Template(explorer_description_template).substitute(
    MAX_SEARCH_ITERATIONS=3
)

planner_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "planner_system.md").read_text(encoding="utf-8")
planner_description = (Path(PARENT_FOLDER_PATH) / "prompts" / "planner_description.md").read_text(encoding="utf-8")

from tools import (
    fetch_oko_page,
    scan_flag,
    submit_answer,
)   

from libs.loggers import LoggerCallbackHandler, agent_logger

langfuse_handler = CallbackHandler()

EXPLORER_CONFIG = {
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": 50, 
}

explorer_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
)

_explorer = create_agent(
    model=explorer_model,
    tools=[
            fetch_oko_page,
            submit_answer,
        ],
    system_prompt=explorer_system,
    name="explorer",
    checkpointer=InMemorySaver(),
)

@tool("explorer", description=explorer_description)
def call_explorer(task: str) -> str:
    
    agent_logger.info(f"[call_explorer] task={task}")
    
    result = _explorer.invoke(
        {"messages": [{"role": "user", "content": task}]},
        config=EXPLORER_CONFIG,
    )
    answer = result["messages"][-1].content
    agent_logger.info(f"[call_explorer] answer={answer}")
    return answer
    
PLANNER_CONFIG = {
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": 50, 
}


planner_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
)
_planner = create_agent(
    model=planner_model,
    tools = [
            scan_flag,
            submit_answer,
    ],

    system_prompt=planner_system,
    name="planner",
    checkpointer=InMemorySaver(),
)


@tool("planner", description=planner_description)
def call_planner(task: str) -> str:
    agent_logger.info(f"[call_planner] task={task}")
    result = _planner.invoke(
        {"messages": [{"role": "user", "content": task}]},
        config=PLANNER_CONFIG,
    )
    answer = result["messages"][-1].content
    agent_logger.info(f"[call_planner] answer={answer}")
    return answer