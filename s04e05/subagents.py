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

AI_DEVS_SECRET = os.environ["AI_DEVS_SECRET"]
TASK_NAME = os.environ["TASK_NAME"]
SOLUTION_URL = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
DB_PATH = Path(os.environ["DB_PATH"])

from libs.loggers import LoggerCallbackHandler, agent_logger
from tools import (
    _RECURSION_LIMIT,
    get_help_cache,
    get_task_input,
    get_database_schema,
    run_database_query,
    get_signature_requirements,
    get_runtime_orders,
    normalize_city,
    normalize_item,
)

langfuse_handler = CallbackHandler()

recon_system = (
    Path(PARENT_FOLDER_PATH) / "prompts" / "recon_system.md"
).read_text(encoding="utf-8")

demand_system = (
    Path(PARENT_FOLDER_PATH) / "prompts" / "demand_system.md"
).read_text(encoding="utf-8")

mapping_system = (
    Path(PARENT_FOLDER_PATH) / "prompts" / "mapping_system.md"
).read_text(encoding="utf-8")

identity_system = (
    Path(PARENT_FOLDER_PATH) / "prompts" / "identity_system.md"
).read_text(encoding="utf-8")

planner_system = (
    Path(PARENT_FOLDER_PATH) / "prompts" / "planner_system.md"
).read_text(encoding="utf-8")

auditor_system = (
    Path(PARENT_FOLDER_PATH) / "prompts" / "auditor_system.md"
).read_text(encoding="utf-8")

RECON_CONFIG = {
    "configurable": {"thread_id": "recon-agent"},
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": _RECURSION_LIMIT,
}

recon_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
    model_kwargs={"parallel_tool_calls": False},
)

recon_agent = create_agent(
    model=recon_model,
    tools=[get_help_cache, get_task_input, get_database_schema, run_database_query],
    system_prompt=recon_system,
    name="recon_agent",
    checkpointer=InMemorySaver(),
)


def run_recon_agent() -> dict:
    """
    Invoke ReconAgent and return discovery results.
    Returns: {
      "discovered_sources": [...],
      "discovered_tables": [...],
      "important_fields": [...],
      "hypotheses": [...],
      "next_steps": [...]
    }
    """
    agent_logger.info("[recon_agent] starting")
    result = recon_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Discover the available sources, schema hints, important fields, and likely next steps.",
                }
            ]
        },
        config=RECON_CONFIG,
    )
    last = result["messages"][-1].content
    agent_logger.info(f"[recon_agent] done — {last}")
    return json.loads(last)


DEMAND_CONFIG = {
    "configurable": {"thread_id": "demand-agent"},
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": _RECURSION_LIMIT,
}

demand_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
    model_kwargs={"parallel_tool_calls": False},
)

demand_agent = create_agent(
    model=demand_model,
    tools=[get_task_input, normalize_city, normalize_item],
    system_prompt=demand_system,
    name="demand_agent",
    checkpointer=InMemorySaver(),
)


def run_demand_agent() -> dict:
    """
    Invoke DemandAgent and return city demand mapping.
    Returns: {"CityName": {"item": quantity_int, ...}, ...}
    """
    agent_logger.info("[demand_agent] starting")
    result = demand_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Extract all participating cities and their required goods and quantities from the task input.",
                }
            ]
        },
        config=DEMAND_CONFIG,
    )
    last = result["messages"][-1].content
    agent_logger.info(f"[demand_agent] done — {last}")
    return json.loads(last)


MAPPING_CONFIG = {
    "configurable": {"thread_id": "mapping-agent"},
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": _RECURSION_LIMIT,
}

mapping_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
    model_kwargs={"parallel_tool_calls": False},
)

mapping_agent = create_agent(
    model=mapping_model,
    tools=[get_database_schema, run_database_query, normalize_city],
    system_prompt=mapping_system,
    name="mapping_agent",
    checkpointer=InMemorySaver(),
)


def run_mapping_agent() -> dict:
    """
    Invoke MappingAgent and return city-to-destination mapping.
    Returns: {"CityName": {"destination": "code", "evidence": [...]}, ...}
    """
    agent_logger.info("[mapping_agent] starting")
    result = mapping_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Determine destination codes for all required cities using database evidence.",
                }
            ]
        },
        config=MAPPING_CONFIG,
    )
    last = result["messages"][-1].content
    agent_logger.info(f"[mapping_agent] done — {last}")
    return json.loads(last)


IDENTITY_CONFIG = {
    "configurable": {"thread_id": "identity-agent"},
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": _RECURSION_LIMIT,
}

identity_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
    model_kwargs={"parallel_tool_calls": False},
)

identity_agent = create_agent(
    model=identity_model,
    tools=[get_database_schema, run_database_query, get_signature_requirements],
    system_prompt=identity_system,
    name="identity_agent",
    checkpointer=InMemorySaver(),
)


def run_identity_agent() -> dict:
    """
    Invoke IdentityAgent and return creator and signature guidance.
    Returns: {
      "creator_candidates": {...},
      "selected_creators": {...},
      "signature_requirements": [...],
      "unresolved": [...]
    }
    """
    agent_logger.info("[identity_agent] starting")
    result = identity_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Identify valid creator IDs and the requirements needed for signature generation.",
                }
            ]
        },
        config=IDENTITY_CONFIG,
    )
    last = result["messages"][-1].content
    agent_logger.info(f"[identity_agent] done — {last}")
    return json.loads(last)


PLANNER_CONFIG = {
    "configurable": {"thread_id": "planner-agent"},
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": _RECURSION_LIMIT,
}

planner_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
    model_kwargs={"parallel_tool_calls": False},
)

planner_agent = create_agent(
    model=planner_model,
    tools=[
        run_recon_agent_tool,
        run_demand_agent_tool,
        run_mapping_agent_tool,
        run_identity_agent_tool,
    ],
    system_prompt=planner_system,
    name="planner_agent",
    checkpointer=InMemorySaver(),
)


def run_planner_agent() -> dict:
    """
    Invoke PlannerAgent and return the consolidated execution plan.
    Returns: {
      "plan_ready": bool,
      "orders": [...],
      "missing": [...],
      "notes": [...]
    }
    """
    agent_logger.info("[planner_agent] starting")
    result = planner_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Build a complete execution plan with one order per city using the outputs of the other agents.",
                }
            ]
        },
        config=PLANNER_CONFIG,
    )
    last = result["messages"][-1].content
    agent_logger.info(f"[planner_agent] done — {last}")
    return json.loads(last)


AUDITOR_CONFIG = {
    "configurable": {"thread_id": "auditor-agent"},
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": _RECURSION_LIMIT,
}

auditor_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
    model_kwargs={"parallel_tool_calls": False},
)

auditor_agent = create_agent(
    model=auditor_model,
    tools=[run_planner_agent_tool, get_runtime_orders],
    system_prompt=auditor_system,
    name="auditor_agent",
    checkpointer=InMemorySaver(),
)


def run_auditor_agent() -> dict:
    """
    Invoke AuditorAgent and return audit comparison results.
    Returns: {
      "pass": bool,
      "missing_orders": [...],
      "header_mismatches": [...],
      "item_mismatches": [...],
      "notes": [...]
    }
    """
    agent_logger.info("[auditor_agent] starting")
    result = auditor_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Compare the current order state with the execution plan and report all mismatches.",
                }
            ]
        },
        config=AUDITOR_CONFIG,
    )
    last = result["messages"][-1].content
    agent_logger.info(f"[auditor_agent] done — {last}")
    return json.loads(last)


@tool
def run_recon_agent_tool() -> str:
    """
    Run the ReconAgent sub-agent.
    Returns extracted data as JSON string.
    """
    data = run_recon_agent()
    agent_logger.info("[supervisor] recon_agent returned data")
    return json.dumps(data, ensure_ascii=False)


@tool
def run_demand_agent_tool() -> str:
    """
    Run the DemandAgent sub-agent.
    Returns extracted data as JSON string.
    """
    data = run_demand_agent()
    agent_logger.info(f"[supervisor] demand_agent returned {list(data.keys())}")
    return json.dumps(data, ensure_ascii=False)


@tool
def run_mapping_agent_tool() -> str:
    """
    Run the MappingAgent sub-agent.
    Returns extracted data as JSON string.
    """
    data = run_mapping_agent()
    agent_logger.info(f"[supervisor] mapping_agent returned {list(data.keys())}")
    return json.dumps(data, ensure_ascii=False)


@tool
def run_identity_agent_tool() -> str:
    """
    Run the IdentityAgent sub-agent.
    Returns extracted data as JSON string.
    """
    data = run_identity_agent()
    agent_logger.info("[supervisor] identity_agent returned data")
    return json.dumps(data, ensure_ascii=False)


@tool
def run_planner_agent_tool() -> str:
    """
    Run the PlannerAgent sub-agent.
    Returns extracted data as JSON string.
    """
    data = run_planner_agent()
    agent_logger.info("[supervisor] planner_agent returned data")
    return json.dumps(data, ensure_ascii=False)


@tool
def run_auditor_agent_tool() -> str:
    """
    Run the AuditorAgent sub-agent.
    Returns extracted data as JSON string.
    """
    data = run_auditor_agent()
    agent_logger.info("[supervisor] auditor_agent returned data")
    return json.dumps(data, ensure_ascii=False)
