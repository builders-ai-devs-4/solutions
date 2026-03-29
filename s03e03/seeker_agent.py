import os
import sys
from pathlib import Path
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openrouter import ChatOpenRouter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.loggers import agent_logger, LoggerCallbackHandler
from tools import scan_flag, submit_answer, _RECURSION_LIMIT

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]

seeker_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "seeker_system.md").read_text(encoding="utf-8")

SEEKER_CONFIG = {
    "configurable": {"thread_id": "reactor-seeker"},
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

        submit_answer,
        scan_flag,
    ],
    system_prompt=seeker_system,
    name="seeker",
    checkpointer=InMemorySaver(),
)