import os
import sys
from dotenv import load_dotenv
from string import Template

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.loggers import LoggerCallbackHandler, agent_logger
from libs.generic_helpers import get_path_from_url, save_file
from libs.logger import get_logger

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

DRONE_MAP_TEMPLATE_URL = os.getenv('SOURCE_URL1')
DRONE_DOCS_URL = os.getenv('SOURCE_URL2')
PWR_ID_CODE = os.getenv('PWR_ID_CODE')

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
date_folder_path = parent_folder_path / DATA_FOLDER
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME

os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)
os.environ["DATA_FOLDER_PATH"] = str(date_folder_path)

drone_map_template = Template(DRONE_MAP_TEMPLATE_URL)
drone_map_url = drone_map_template.substitute(ai_devs_secret=AI_DEVS_SECRET)
os.environ["DRONE_MAP_URL"] = str(drone_map_url)


if __name__ == "__main__":
    
    agent_logger.info(f"[task] Starting task: {TASK_NAME}")
  