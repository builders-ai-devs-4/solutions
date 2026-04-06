import json
import os
import sys
from unittest import result
from dotenv import load_dotenv
from string import Template

from langfuse import Langfuse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.database import Database
from libs.generic_helpers import get_filename_from_url, save_file

from pathlib import Path
import requests

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
TASK           = os.getenv('TASK')
SOLUTION_URL   = os.getenv('SOLUTION_URL')
DATA_FOLDER    = os.getenv('DATA_FOLDER')
TASK_NAME      = os.getenv('TASK_NAME')

FOOD_4_CITIES_URL = os.getenv('SOURCE_URL1')
MODULE_NAME = "task"

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
date_folder_path = parent_folder_path / DATA_FOLDER
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
food_4_cities_dir_path = task_data_folder / "food_4_cities"
db_dir_path = task_data_folder / "db"
os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)
os.environ["DATA_FOLDER_PATH"] = str(date_folder_path)
os.environ["FOOD_4_CITIES_DIR_PATH"] = str(food_4_cities_dir_path)
os.environ["DB_DIR_PATH"] = str(db_dir_path)
db_dir_path.mkdir(parents=True, exist_ok=True)
db_path = db_dir_path / "foodawarehouse.duckdb"
os.environ["DB_PATH"] = str(db_path)


# Singleton initialization of Langfuse (only once, at startup)
# This ensures that all agents and tools share the same Langfuse instance and configuration.

Langfuse(
    public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
    secret_key=os.environ["LANGFUSE_SECRET_KEY"],
)

# from supervisor_agent import SUPERVISOR_CONFIG, supervisor
from libs.loggers import LoggerCallbackHandler, agent_logger
from modules.help import get_help


def bootstrap_static_db(db_path: Path, food_4_cities_dir_path: Path, help_result: str) -> None:
    with Database(db_path) as db:
        db.load_json_dir_multi_table(food_4_cities_dir_path)
        db.load_json_string("get_help", help_result, replace=True)


# supervisor_user_template = (
#     Path(parent_folder_path) / "prompts" / "supervisor_user.md"
# ).read_text(encoding="utf-8")

# supervisor_user = Template(supervisor_user_template).substitute(
#     DB_PATH=str(db_path),
# )

if __name__ == "__main__":
   
    agent_logger.info(f"[{MODULE_NAME}] Starting task: {TASK_NAME}")
    result, payload = get_help({"tool": "help"})
    agent_logger.info(f"[{MODULE_NAME}] help={result}")
    
    if not db_path.exists():
        
        filename_from_url = get_filename_from_url(FOOD_4_CITIES_URL)
        agent_logger.info(f"[{MODULE_NAME}] Downloading food4cities data from {FOOD_4_CITIES_URL} to {food_4_cities_dir_path}")
        food_4_cities_dir_path.mkdir(parents=True, exist_ok=True)
        food4cities_file_path = save_file(FOOD_4_CITIES_URL, food_4_cities_dir_path, override=True)

        bootstrap_static_db(db_path, food_4_cities_dir_path, result)
        with Database(db_path) as db:
            agent_logger.info(f"[{MODULE_NAME}] Loading documents directory")
            db.load_json_dir_multi_table(food_4_cities_dir_path)
            db.load_json_string('get_help', result)           


        agent_logger.info(f"[{MODULE_NAME}] DB created at {db_path}")
        

    # result = supervisor.invoke(
    #     {"messages": [{"role": "user", "content": supervisor_user}]},
    #     config=SUPERVISOR_CONFIG,
    # )
    # agent_logger.info(f"[{MODULE_NAME}] {result['messages'][-1].content}")
    
    
  