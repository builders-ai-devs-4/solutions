import os
from pathlib import Path
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from tools import read_file, read_csv, save_file_from_url, scan_flag, send_to_server, count_prompt_tokens
from loggers import LoggerCallbackHandler, agent_logger,get_logger, _log_dir
from langchain_core.callbacks import BaseCallbackHandler

prompt_logger = get_logger("prompt", log_dir=_log_dir(), log_stem="prompt")

CATEGORIZATION_URL = os.environ["CATEGORIZATION_URL"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]

META_PROMPT = (Path(PARENT_FOLDER_PATH) / "prompts" / "meta_prompt.md"
               ).read_text(encoding="utf-8")
SUPERVISOR_SYS_PROMPT = (Path(PARENT_FOLDER_PATH) / "prompts" / "supervisor_system.md"
                     ).read_text(encoding="utf-8")

_EXECUTOR_PROMPT_TEMPLATE = (Path(PARENT_FOLDER_PATH) / "prompts" / "executor_system.md"
                             ).read_text(encoding="utf-8")
EXECUTOR_SYS_PROMPT = _EXECUTOR_PROMPT_TEMPLATE.format(
    CATEGORIZATION_URL=CATEGORIZATION_URL,
    DATA_FOLDER_PATH=DATA_FOLDER_PATH,
)

MAX_TOOL_ITERATIONS = 10  # 10 requests + reset + download CSV ~ 12 tool calls
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 12 + 2  # 122

PROMPT_ENGINEER_CONFIG = {
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": _RECURSION_LIMIT,
}

# ── Subagent 1: Prompt Engineer ──────────────────────────────────────────────


_prompt_engineer = create_agent(
    model="openai:gpt-5.1",

    tools=[count_prompt_tokens],
    system_prompt=META_PROMPT,
    name="prompt_engineer",
)

@tool("prompt_engineer", description=(
    "Creates or refines a DNG/NEU classification prompt. "
    "Input: task description + optionally the previous prompt and list of server errors."))
def call_prompt_engineer(task: str) -> str:
    result = _prompt_engineer.invoke(
        {"messages": [{"role": "user", "content": task}]},
        config=PROMPT_ENGINEER_CONFIG,
    )
    answer = result["messages"][-1].content
    agent_logger.info(f"[prompt_engineer] {answer}")
    prompt_logger.info(answer)
    return answer

# ── Subagent 2: Executor ──────────────────────────────────────────────────────

EXECUTOR_CONFIG = {
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": 50, 
    # Executor performs: 1× reset + 1× download CSV + 1× read_csv + 10× send_to_server + 10× scan_flag = ~23 tool calls → 23 * 2 + 2 = 48
}

_executor = create_agent(
    model="openai:gpt-5-mini",

    tools=[send_to_server, save_file_from_url, read_csv, scan_flag],
    system_prompt=EXECUTOR_SYS_PROMPT,
    name="executor",
)

from models import ExecutorResult

@tool("executor", description=(
    "Runs the full classification cycle: reset server → download CSV → read rows → "
    "send 10 classification queries → scan each response for a flag {FLG:...}. "
    "Stops immediately if a flag is found or if server returns 'classification error'/'budget exceeded'. "
    "Input: ready-to-use classification prompt. "
    "Returns ExecutorResult JSON with status, responses and errors."
))
def call_executor(classification_prompt: str) -> str:
    result = _executor.invoke(
        {"messages": [{"role": "user", "content": classification_prompt}]},
        config=EXECUTOR_CONFIG,
    )
    answer = result["messages"][-1].content
    
    try:
        parsed = ExecutorResult.model_validate_json(answer)
        agent_logger.info(
            f"[executor] status={parsed.status} "
            f"responses={len(parsed.responses)} errors={len(parsed.errors)}"
        )
        if parsed.errors:
            for e in parsed.errors:
                agent_logger.warning(f"[executor] error id={e.id} code={e.server_code} msg={e.server_message}")
        return parsed.model_dump_json()  
    except Exception as exc:
        agent_logger.warning(f"[executor] Could not parse structured response: {exc}")
        return answer 


# --- Supervisor ---

SUPERVISOR_CONFIG = {
    "configurable": {"thread_id": "s02e01-supervisor"},
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": _RECURSION_LIMIT,
}

supervisor = create_agent(
    model="openai:gpt-5-mini",
    tools=[call_prompt_engineer, call_executor, count_prompt_tokens],
    system_prompt=SUPERVISOR_SYS_PROMPT,
    name="supervisor",
    checkpointer=InMemorySaver(),
)