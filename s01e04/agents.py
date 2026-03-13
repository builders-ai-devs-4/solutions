import asyncio
import json
import os
from pathlib import Path
import sys
import uuid
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from libs.generic_helpers import read_file_base64, read_file_text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from libs.filetype_detect import detect_file_type
from libs.logger import get_logger
from tools import IndexEntry, LoggerCallbackHandler, get_file_list, load_index, read_file, save_file_from_url
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field


class DeclarationForm(BaseModel):
    """Completed SPK transport declaration, formatted exactly as the template."""
    declaration: str = Field(
        description="The fully completed SPK declaration form, reproduced character-for-character from the template."
    )

# Maximum number of rounds: LLM calls a tool → tool returns a result.
# Each round = 2 LangGraph steps (one LLM step + one tool step).
MAX_TOOL_ITERATIONS = 20

# recursion_limit is LangGraph's internal step counter — not an iteration counter.
# Formula: each tool iteration = 2 steps, plus 1 step for the final LLM response,
# plus 1 safety margin = MAX_TOOL_ITERATIONS * 2 + 2.
# When the limit is reached, the agent ends gracefully with a message instead of raising an exception.
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 2 + 2

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
    model="openai:gpt-4o-mini",
    tools=[save_file_from_url, get_file_list, read_file],
    system_prompt=asset_collector_agent_system_prompt,
    checkpointer=memory,
)

_ANALYSIS_PROMPT_PATH = PARENT_FOLDER_PATH / "prompts" / "memory_builder_agent_system_prompt.md"
_ANALYSIS_SYSTEM_PROMPT = _ANALYSIS_PROMPT_PATH.read_text(encoding="utf-8")

def analyze_text_file(text_content: str, filename: str) -> IndexEntry:
    """Send text file content to LLM and return structured IndexEntry."""
    llm = ChatOpenAI(model="openai:gpt-5-mini", temperature=0)
    messages = [
        SystemMessage(_ANALYSIS_SYSTEM_PROMPT),
        HumanMessage(f"File: {filename}\n\n{text_content}"),
    ]
    return llm.with_structured_output(IndexEntry).invoke(messages)


def analyze_image_file(base64_content: str, filename: str) -> IndexEntry:
    """Send image (as base64) to vision LLM and return structured IndexEntry."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    messages = [
        SystemMessage(_ANALYSIS_SYSTEM_PROMPT),
        HumanMessage(content=[
            {"type": "text", "text": f"File: {filename}"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_content}"}},
        ]),
    ]
    return llm.with_structured_output(IndexEntry).invoke(messages)


def build_memory_index(data_folder: Path, index_path: Path) -> None:
    index = load_index(index_path)
    already_indexed = set(index["files"].keys())

    files = [f for f in data_folder.iterdir() if f.is_file() and f.name != "index.json"]

    for file_path in files:
        if file_path.name in already_indexed:
            agent_logger.info(f"Skipping {file_path.name} (already indexed)")
            continue

        agent_logger.info(f"Processing {file_path.name}")
        try:
            info = detect_file_type(file_path)
            raw = read_file_text(file_path) if info.final_kind == "text" \
                  else read_file_base64(file_path)
            entry = analyze_text_file(raw, file_path.name) if info.final_kind == "text" \
                    else analyze_image_file(raw, file_path.name)
            save_entry_to_index(index_path, file_path, info.final_kind, entry)
            agent_logger.info(f"Indexed {file_path.name} | form_template={entry.is_form_template}")
        except Exception as e:
            agent_logger.error(f"Failed to process {file_path.name}: {e}")
            
def save_entry_to_index(index_path: Path, file_path: Path, file_type: str, entry: IndexEntry) -> None:
    """Add or update a single file entry in the memory index. Reads and rewrites the full index file."""
    index = load_index(index_path)
    index["files"][file_path.name] = {
        "path": str(file_path),
        "type": file_type,
        **entry.model_dump(),
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


_REACT_PROMPT_PATH = PROMPTS_DIR / "react_agent_system_prompt.md"
_react_system_prompt = _REACT_PROMPT_PATH.read_text(encoding="utf-8")

react_logger = get_logger(
    "agent.react",
    log_dir=Path(os.getenv("DATA_FOLDER_PATH")) / "logs",
    log_stem="react_agent",
)

react_agent = create_agent(
    model="openai:gpt-5-mini",
    tools=[read_file, get_file_list],
    system_prompt=_react_system_prompt,
    response_format=DeclarationForm,
    checkpointer=memory,
)

def fill_form(index_json_path: Path) -> DeclarationForm:
    result = react_agent.invoke(
        {"messages": [{
            "role": "user",
            "content": f"index_json_path: {index_json_path}"
        }]},
        config={
            "configurable": {"thread_id": f"react-{uuid.uuid4()}"},
            "callbacks": [LoggerCallbackHandler(react_logger)],
            "recursion_limit": _RECURSION_LIMIT,
        },
    )
    return result["structured_response"]