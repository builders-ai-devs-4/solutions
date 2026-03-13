import os
import sys
from dotenv import load_dotenv
from string import Template

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import save_file
from libs.logger import get_logger

from pathlib import Path
import requests
import json


load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AI_DEVS_SECRET =  os.getenv('AI_DEVS_SECRET')
HUB_URL =  os.getenv('HUB_URL')
TASK =  os.getenv('TASK')
SOLUTION_URL =  os.getenv('SOLUTION_URL')
INDEX_MD_URL =  os.getenv('SOURCE_URL1')
DATA_FOLDER =  os.getenv('DATA_FOLDER')
TASK_NAME =  os.getenv('TASK_NAME')


import json

current_folder = Path(__file__)
parent_folder = current_folder.parent
task_data_folder = parent_folder / DATA_FOLDER / TASK_NAME

# logger = get_logger(TASK, log_dir=parent_folder / DATA_FOLDER/ "logs")

os.environ["DATA_FOLDER_PATH"] = str(task_data_folder)
    
if __name__ == '__main__':
    
    index_md_file = save_file(INDEX_MD_URL, task_data_folder)




