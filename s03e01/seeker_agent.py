from pathlib import Path
import sys
import os
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openrouter import ChatOpenRouter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from libs.loggers import agent_logger, LoggerCallbackHandler


AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL        = os.environ["SOLUTION_URL"]

DATA_FOLDER_PATH    = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH  = os.environ["PARENT_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]


from tools import analyze_operator_notes, _RECURSION_LIMIT, run_sensor_validation, scan_flag, send_anomalies_to_central

seeker_system = (Path(PARENT_FOLDER_PATH) / "prompts" / "seeker_system.md"
                     ).read_text(encoding="utf-8")

SEEKER_CONFIG = {
    "configurable": {"thread_id": "s03e01-seeker"},
    "callbacks": [LoggerCallbackHandler(agent_logger)],
    "recursion_limit": _RECURSION_LIMIT,
}

seeker_model = ChatOpenRouter(
    model="google/gemini-3-flash-preview",
    temperature=0,
)

seeker = create_agent(
    model=seeker_model,
    tools=[
        analyze_operator_notes,
        run_sensor_validation,
        send_anomalies_to_central,
        scan_flag
    ],
    system_prompt=seeker_system,
    name="seeker",
    checkpointer=InMemorySaver(),
)
