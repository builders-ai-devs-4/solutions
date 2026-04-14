import os
import sys
from pathlib import Path
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openrouter import ChatOpenRouter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
parent_folder_path = Path(__file__).parent.parent
sys.path.insert(0, str(parent_folder_path.parent)) 
sys.path.insert(0, str(Path(__file__).parent)) 
sys.path.insert(0, str(parent_folder_path)) 

from langfuse.langchain import CallbackHandler
AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]

from libs.loggers import agent_logger, LoggerCallbackHandler
from tools import get_cities_for_item, search_items, _RECURSION_LIMIT

langfuse_handler = CallbackHandler()

seeker_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "seeker_system.md").read_text(encoding="utf-8")

SEEKER_CONFIG = {
    "configurable": {"thread_id": "negotiations-seeker"},
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": _RECURSION_LIMIT,
}

seeker_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
)

seeker = create_agent(
    model=seeker_model,
    tools=[

        get_cities_for_item,
        search_items
    ],
    system_prompt=seeker_system,
    name="seeker",
    checkpointer=InMemorySaver(),
)