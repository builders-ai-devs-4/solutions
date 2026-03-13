import asyncio
import os
from pathlib import Path
import sys
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from libs.logger import get_logger
from s01e04.tools import get_file_list, read_file, save_file_from_url

# Maximum number of rounds: LLM calls a tool → tool returns a result.
# Each round = 2 LangGraph steps (one LLM step + one tool step).
MAX_TOOL_ITERATIONS = 5

# recursion_limit is LangGraph's internal step counter — not an iteration counter.
# Formula: each tool iteration = 2 steps, plus 1 step for the final LLM response,
# plus 1 safety margin = MAX_TOOL_ITERATIONS * 2 + 2.
# When the limit is reached, the agent ends gracefully with a message instead of raising an exception.
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 2 + 2  # 12

memory = InMemorySaver()

PARENT_FOLDER_PATH = Path(os.getenv("PARENT_FOLDER_PATH"))
PROMPTS_DIR = PARENT_FOLDER_PATH / "prompts"
asset_collector_agent_system_prompt = (PROMPTS_DIR / "asset_collector_agent_system_prompt.md").read_text(encoding="utf-8")

agent_logger = get_logger(
    "agent.asset_collector",
    log_dir=Path(os.getenv("DATA_FOLDER_PATH")) / "logs",
    log_stem="asset_collector_agent",
)

asset_collector_agent = create_agent(
    model="openai:gpt-5-mini",
    tools=[save_file_from_url, get_file_list, read_file],
    system_prompt=asset_collector_agent_system_prompt,
    checkpointer=memory,
)
