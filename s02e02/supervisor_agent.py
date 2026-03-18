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

MAP_URL = os.environ["MAP_URL"]
MAP_RESET_URL = os.environ["MAP_RESET_URL"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]

# META_PROMPT = (Path(PARENT_FOLDER_PATH) / "prompts" / "meta_prompt.md"
#                ).read_text(encoding="utf-8")
SUPERVISOR_SYS_PROMPT = (Path(PARENT_FOLDER_PATH) / "prompts" / "supervisor_system.md"
                     ).read_text(encoding="utf-8")

# _EXECUTOR_PROMPT_TEMPLATE = (Path(PARENT_FOLDER_PATH) / "prompts" / "executor_system.md"
#                              ).read_text(encoding="utf-8")
# EXECUTOR_SYS_PROMPT = _EXECUTOR_PROMPT_TEMPLATE.format(
#     MAP_RESET_URL=MAP_RESET_URL,
#     MAP_URL=MAP_URL,
#     DATA_FOLDER_PATH=DATA_FOLDER_PATH,
# )

MAX_TOOL_ITERATIONS = 10  # 10 requests + reset + download CSV ~ 12 tool calls
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 12 + 2  # 122

# PROMPT_ENGINEER_CONFIG = {
#     "callbacks": [LoggerCallbackHandler(agent_logger)],
#     "recursion_limit": _RECURSION_LIMIT,
# }


SUPERVISOR_CONFIG = {
    "configurable": {"thread_id": "s02e01-supervisor"},
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": _RECURSION_LIMIT,
}

supervisor = create_agent(
    model="openai:gpt-5-mini",
    tools=[ count_prompt_tokens],
    system_prompt=SUPERVISOR_SYS_PROMPT,
    name="supervisor",
    checkpointer=InMemorySaver(),
)