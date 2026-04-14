import os
import sys
from string import Template
from pathlib import Path
import time
from dotenv import load_dotenv
import requests
from pydantic import BaseModel, Field

parent_folder_path = Path(__file__).parent.parent
load_dotenv(parent_folder_path / ".env") 
sys.path.insert(0, str(parent_folder_path.parent)) 
sys.path.insert(0, str(Path(__file__).parent)) 
sys.path.insert(0, str(parent_folder_path)) 

load_dotenv()

AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
SOLUTION_URL   = os.getenv('SOLUTION_URL')
DATA_FOLDER    = os.getenv('DATA_FOLDER')
TASK_NAME      = os.getenv('TASK_NAME')
AGENTIC_API_URL = os.getenv('AGENTIC_API_URL')
CSV_FILES_URL = os.getenv('SOURCE_URL1')

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
date_folder_path = parent_folder_path / DATA_FOLDER
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
db_dir_path = task_data_folder / "db"
csvs_dir_path = task_data_folder / "csvs"
os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)
os.environ["DATA_FOLDER_PATH"] = str(date_folder_path)
os.environ["DB_DIR_PATH"] = str(db_dir_path)
os.environ["CSVS_DIR_PATH"] = str(csvs_dir_path)
db_dir_path.mkdir(parents=True, exist_ok=True)
csvs_dir_path.mkdir(parents=True, exist_ok=True)
db_path = db_dir_path / "negotiations.db"
os.environ["DB_PATH"] = str(db_path)

from libs.loggers import LoggerCallbackHandler, agent_logger
from libs.central_client import _scan_flag_in_response
from libs.central_client import _post_to_central
from libs.tomarkdown import transform_html_to_markdown
from resources.preparation import creating_db, save_extracted_csv_files
from models import SubmitAnswerInputCheck, SubmitAnswerInputTools, ToolEntry

MODULE_NAME = "task"

POLL_INTERVAL = 10    # seconds between polls
POLL_TIMEOUT  = 300   # max time to wait in seconds
INITIAL_WAIT  = 15    # time before the first check

tools = SubmitAnswerInputTools(tools=[
ToolEntry(
    URL=f"{AGENTIC_API_URL}/connections",
    description=(
        "Find cities selling a specific item. "
        "Pass natural language item description in 'params', "
        "e.g. 'copper wire 2mm'. "
        "Returns comma-separated city names. "
        "Call once per item, then intersect results to find cities with ALL items."
    )
)
])

check = SubmitAnswerInputCheck(action="check")

if __name__ == "__main__":
    
    agent_logger.info(f"[{MODULE_NAME}] Starting task: {TASK_NAME}")
    if not db_path.exists():
        agent_logger.info(f"[{MODULE_NAME}] Database not found. Creating new database at {db_path}")
        md = transform_html_to_markdown(csvs_dir_path, CSV_FILES_URL)
        agent_logger.info(f"[{MODULE_NAME}] Extracted markdown saved to {md}")
        save_extracted_csv_files(CSV_FILES_URL, csvs_dir_path, md)
        agent_logger.info(f"[{MODULE_NAME}] CSV files extracted and saved to {csvs_dir_path}")
        creating_db(csvs_dir_path, db_path)
        agent_logger.info(f"[{MODULE_NAME}] Database created at {db_path}")

    # 1. Registration of tools in the central system
    json_tools, payload_tools = _post_to_central(tools.model_dump())
    agent_logger.info(f"[{MODULE_NAME}] Tools registration response: {json_tools}")

    # 2. First wait before polling to give the system time to process the registration and for the agent to potentially invoke the tool. This is important to avoid
    agent_logger.info(f"[{MODULE_NAME}] Waiting {INITIAL_WAIT}s before polling...")
    time.sleep(INITIAL_WAIT)

    # 3. Polling loop
    elapsed = 0
    while elapsed < POLL_TIMEOUT:
        json_check, payload_check = _post_to_central(check.model_dump())
        agent_logger.info(f"[{MODULE_NAME}] Check response: {json_check}")

        flag = _scan_flag_in_response(str(json_check))
        if flag:
            agent_logger.info(f"[{MODULE_NAME}] Flag found: {flag}")
            break

        agent_logger.info(f"[{MODULE_NAME}] No flag yet, retrying in {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
    else:
        agent_logger.warning(f"[{MODULE_NAME}] Timeout after {POLL_TIMEOUT}s — no flag received.")