import os
import sys
from string import Template
from pathlib import Path
from dotenv import load_dotenv

parent_folder_path = Path(__file__).parent.parent
load_dotenv(parent_folder_path / ".env") 
sys.path.insert(0, str(parent_folder_path.parent)) 
sys.path.insert(0, str(Path(__file__).parent)) 

import requests


load_dotenv()

AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
SOLUTION_URL   = os.getenv('SOLUTION_URL')
DATA_FOLDER    = os.getenv('DATA_FOLDER')
TASK_NAME      = os.getenv('TASK_NAME')

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
date_folder_path = parent_folder_path / DATA_FOLDER
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
sensors_dir_path = task_data_folder / "sensors"
db_dir_path = task_data_folder / "db"
os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)
os.environ["DATA_FOLDER_PATH"] = str(date_folder_path)
os.environ["SENSORS_DIR_PATH"] = str(sensors_dir_path)
os.environ["DB_DIR_PATH"] = str(db_dir_path)
db_dir_path.mkdir(parents=True, exist_ok=True)
db_path = db_dir_path / "sensors.db"
os.environ["DB_PATH"] = str(db_path)

from libs.loggers import LoggerCallbackHandler, agent_logger
from langfuse import Langfuse, get_client

