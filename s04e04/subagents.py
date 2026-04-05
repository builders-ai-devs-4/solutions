import json
import os
import sys
from pathlib import Path

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openrouter import ChatOpenRouter
from langfuse.langchain import CallbackHandler
from langchain_core.tools import tool


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
DB_PATH            = Path(os.environ["DB_PATH"])


from libs.loggers import LoggerCallbackHandler, agent_logger
from database_sqlite_fts import Database
from tools import get_all_transactions, get_announcements_doc, get_notes_doc, log_dropped_person, normalize_city, normalize_item, _RECURSION_LIMIT


langfuse_handler = CallbackHandler()

explorer_cities_system = (
    Path(PARENT_FOLDER_PATH) / "prompts" / "explorer_cities_system.md"
).read_text(encoding="utf-8")


explorer_goods_system = (
    Path(PARENT_FOLDER_PATH) / "prompts" / "explorer_goods_system.md"
).read_text(encoding="utf-8")

explorer_persons_system = (
    Path(PARENT_FOLDER_PATH) / "prompts" / "explorer_persons_system.md"
).read_text(encoding="utf-8")

EXPLORER_CITIES_CONFIG = {
    "configurable": {"thread_id": "explorer-cities"},
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": _RECURSION_LIMIT,
}

explorer_cities_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
    model_kwargs={"parallel_tool_calls": False},
)

explorer_cities = create_agent(
    model=explorer_cities_model,
    tools=[get_announcements_doc, normalize_city, normalize_item],
    system_prompt=explorer_cities_system,
    name="explorer_cities",
    checkpointer=InMemorySaver(),
)


def run_explorer_cities() -> dict:
    """
    Invoke ExplorerMiasta and return city demand mapping.
    Returns: {"CityName": {"item": quantity_int, ...}, ...}
    """
    agent_logger.info("[explorer_cities] starting")
    result = explorer_cities.invoke(
        {"messages": [{"role": "user", "content": "Extract the demand requirements of all cities from the announcements."}]},
        config=EXPLORER_CITIES_CONFIG,
    )
    last = result["messages"][-1].content
    agent_logger.info(f"[explorer_cities] done — {last}")
    return json.loads(last)


EXPLORER_GOODS_CONFIG = {
    "configurable": {"thread_id": "explorer-goods"},
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": _RECURSION_LIMIT,
}

explorer_goods_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
    model_kwargs={"parallel_tool_calls": False},
)

explorer_goods = create_agent(
    model=explorer_goods_model,
    tools=[get_all_transactions, normalize_city, normalize_item],
    system_prompt=explorer_goods_system,
    name="explorer_goods",
    checkpointer=InMemorySaver(),
)

def run_explorer_goods() -> dict:
    """
    Invoke ExplorerTowary and return goods→cities mapping.
    Returns: {"item": ["City1", "City2"], ...}
    """
    agent_logger.info("[explorer_goods] starting")
    result = explorer_goods.invoke(
        {"messages": [{"role": "user", "content": "Build a goods→cities map from the transactions table."}]},
        config=EXPLORER_GOODS_CONFIG,
    )
    last = result["messages"][-1].content
    agent_logger.info(f"[explorer_goods] done — {last}")
    return json.loads(last)

EXPLORER_PERSONS_CONFIG = {
    "configurable": {"thread_id": "explorer-persons"},
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": _RECURSION_LIMIT,
}

explorer_persons_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
    model_kwargs={"parallel_tool_calls": False},
)

explorer_persons = create_agent(
    model=explorer_persons_model,
    tools=[get_notes_doc, normalize_city, log_dropped_person],
    system_prompt=explorer_persons_system,
    name="explorer_persons",
    checkpointer=InMemorySaver(),
)

def run_explorer_persons() -> dict:
    """
    Invoke ExplorerOsoby and return person→city mapping.
    Returns: {"Full Name": "CityName", ...}
    """
    agent_logger.info("[explorer_persons] starting")
    result = explorer_persons.invoke(
        {"messages": [{"role": "user", "content": "Extract person→city pairs from Natan's conversations."}]},
        config=EXPLORER_PERSONS_CONFIG,
    )
    
    last = result["messages"][-1].content
    agent_logger.info(f"[explorer_persons] done — {last}")
    return json.loads(last)


@tool
def run_explorer_cities_tool() -> str:
    """
    Run the ExplorerMiasta sub-agent to extract city demand data from announcements.
    Returns extracted data as JSON string: {"CityName": {"item": quantity, ...}, ...}
    """
    data = explorer_cities.run()
    agent_logger.info(f"[supervisor] explorer_cities returned {list(data.keys())}")
    return json.dumps(data, ensure_ascii=False)


@tool
def run_explorer_persons_tool() -> str:
    """
    Run the ExplorerOsoby sub-agent to extract person→city assignments from conversation notes.
    Returns extracted data as JSON string: {"Full Name": "CityName", ...}
    """
    data = explorer_persons.run()
    agent_logger.info(f"[supervisor] explorer_persons returned {list(data.keys())}")
    return json.dumps(data, ensure_ascii=False)


@tool
def run_explorer_goods_tool() -> str:
    """
    Run the ExplorerTowary sub-agent to extract goods→source cities from transactions.
    Returns extracted data as JSON string: {"item": ["City1", "City2"], ...}
    """
    data = explorer_goods.run()
    agent_logger.info(f"[supervisor] explorer_goods returned {list(data.keys())}")
    return json.dumps(data, ensure_ascii=False)
