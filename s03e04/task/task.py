import os
import sys
from string import Template
from pathlib import Path
from dotenv import load_dotenv
import requests
from pydantic import BaseModel, Field


parent_folder_path = Path(__file__).parent.parent
load_dotenv(parent_folder_path / ".env") 
sys.path.insert(0, str(parent_folder_path.parent)) 
sys.path.insert(0, str(Path(__file__).parent)) 
sys.path.insert(0, str(parent_folder_path)) 

load_dotenv()
from libs.central_client import _post_to_central
from libs.generic_helpers import save_file
from libs.tomarkdown import transform_html_to_markdown
from libs.database import Database
from resources.preparation import creating_db, save_extracted_csv_files
from task.models import SubmitAnswerInputCheck, SubmitAnswerInputTools, ToolEntry

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

MODULE_NAME = "task"

tools = SubmitAnswerInputTools(tools=[
    ToolEntry(URL=f"{AGENTIC_API_URL}/tools/submit_answer", 
              description="Submit the final answer to the central verification endpoint. Call this only when you have the complete and confirmed answer ready. After calling this tool, ALWAYS call scan_flag on the response."),
    ToolEntry(URL=f"{AGENTIC_API_URL}/tools/scan_flag", 
              description="Search for a success flag matching the pattern {FLG:...} in the given text. Call this tool to analyze the server's response after submitting a solution to verify task completion."), 
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

    json_tools, payload_tools = _post_to_central(tools.model_dump())
    json_check, payload_check = _post_to_central(check.model_dump())
    agent_logger.info(f"[{MODULE_NAME}] Tools registration response: {json_tools}")
    agent_logger.info(f"[{MODULE_NAME}] Check action registration response: {json_check}")