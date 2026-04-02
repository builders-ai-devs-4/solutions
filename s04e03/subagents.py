from pathlib import Path
from string import Template
import sys
from langchain_core.tools import tool
import os
from langchain.agents import create_agent
from langchain_openrouter import ChatOpenRouter
from langgraph.checkpoint.memory import InMemorySaver
from langfuse.langchain import CallbackHandler
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]


explorer_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "explorer_system.md").read_text(encoding="utf-8")

explorers_description = (Path(PARENT_FOLDER_PATH) / "prompts" / "explorers_description.md").read_text(encoding="utf-8")

planner_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "planner_system.md").read_text(encoding="utf-8")
planner_description = (Path(PARENT_FOLDER_PATH) / "prompts" / "planner_description.md").read_text(encoding="utf-8")

from tools import (
    poll_results,
    queue_requests,
    get_help,
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
            poll_results,
            queue_requests,
            get_help,
        ],
    system_prompt=explorer_system,
    name="explorer",
    # checkpointer=InMemorySaver(),
)

async def _run_single_explorer(task: str, explorer_id: int) -> dict:
    """
    Runs a single explorer agent instance asynchronously for a given cluster task.

    Args:
        task: Full task description for the explorer, including cluster coordinates,
              transporter drop point, and assigned budget slice.
        explorer_id: Numeric identifier of this explorer instance, used for logging
                     and result tracking.

    Returns:
        Dict with keys:
            explorer_id (int): identifier of this explorer.
            result (str): last message content from the agent. Contains 'FOUND: <coords>'
                          if the target was located, or 'NOT_FOUND' otherwise.
    """
    agent_logger.info(f"[explorer_{explorer_id}] started | task={task}")
    result = await _explorer.ainvoke(
        {"messages": [{"role": "user", "content": task}]},
        config={**EXPLORER_CONFIG, "run_name": f"explorer_{explorer_id}"},
    )
    answer = result["messages"][-1].content
    agent_logger.info(f"[explorer_{explorer_id}] finished | result={answer}")
    return {"explorer_id": explorer_id, "result": answer}


async def _run_explorers_with_cancel(tasks: list[str]) -> dict:
    """
    Runs all explorer tasks concurrently and cancels remaining ones
    as soon as the first explorer reports finding the target.

    Uses asyncio.as_completed so results are processed in arrival order,
    not submission order — the fastest explorer triggers early cancellation.

    Args:
        tasks: List of task descriptions, one per cluster. Each task is passed
               directly to a separate _run_single_explorer instance.

    Returns:
        Dict with keys:
            found (bool): True if any explorer located the target.
            coordinates (str | None): Grid coordinates of the target (e.g. 'F6'),
                                      or None if not found.
            explorer_id (int | None): ID of the explorer that found the target,
                                      or None if not found.
            results (list[dict]): All explorer reports collected before cancellation.
    """
    agent_logger.info(f"[explorers] launching {len(tasks)} explorers in parallel")
    loop = asyncio.get_event_loop()
    pending = [asyncio.create_task(_run_single_explorer(task, i)) for i, task in enumerate(tasks)]
    all_results = []

    for coro in asyncio.as_completed(pending):
        try:
            result = await coro
            all_results.append(result)
            agent_logger.info(
                f"[explorers] explorer_{result['explorer_id']} reported | "
                f"completed={len(all_results)}/{len(tasks)} | result={result['result']}"
            )

            if "FOUND:" in result["result"]:
                coords = result["result"].split("FOUND:")[-1].strip()
                cancelled = sum(1 for t in pending if not t.done())
                agent_logger.info(
                    f"[explorers] target found by explorer_{result['explorer_id']} "
                    f"at {coords} | cancelling {cancelled} remaining explorer(s)"
                )
                for t in pending:
                    if not t.done():
                        t.cancel()
                return {
                    "found": True,
                    "coordinates": coords,
                    "explorer_id": result["explorer_id"],
                    "results": all_results,
                }
        except asyncio.CancelledError:
            agent_logger.info(
                f"[explorers] one explorer cancelled after target already found"
            )

    agent_logger.info(
        f"[explorers] all {len(tasks)} explorers finished | target not found"
    )
    return {"found": False, "coordinates": None, "explorer_id": None, "results": all_results}


@tool(
    "call_explorers",
    description=explorer_description,
)
def call_explorers(tasks: list[str]) -> dict:
    """
    Entry point for parallel multi-cluster exploration with early cancellation.

    Synchronous wrapper around _run_explorers_with_cancel, required because
    LangChain tools must be synchronous when used with create_agent.
    All async logic is isolated in the private helper functions.

    Args:
        tasks: List of task descriptions, one per cluster. Should include
               block coordinates, transporter drop point, and budget slice
               for each cluster.

    Returns:
        Dict with keys:
            found (bool): whether the target was located in any cluster.
            coordinates (str | None): grid coordinates if found, e.g. 'F6'.
            explorer_id (int | None): ID of the explorer that found the target.
            results (list[dict]): all collected explorer reports.
    """
    agent_logger.info(f"[call_explorers] invoked | clusters={len(tasks)}")
    result = asyncio.run(_run_explorers_with_cancel(tasks))
    agent_logger.info(
        f"[call_explorers] done | found={result['found']} | "
        f"coordinates={result['coordinates']} | "
        f"explorer_id={result['explorer_id']}"
    )
    return result

PLANNER_CONFIG = {
    "callbacks": [LoggerCallbackHandler(agent_logger), langfuse_handler],
    "recursion_limit": 100, 
}


planner_model = ChatOpenRouter(
    model="openai/gpt-5-mini",
    temperature=0,
)
_planner = create_agent(
    model=planner_model,
    tools = [
            poll_results,
            queue_requests,
            get_help,
    ],

    system_prompt=planner_system,
    name="planner",
    # checkpointer=InMemorySaver(),
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

