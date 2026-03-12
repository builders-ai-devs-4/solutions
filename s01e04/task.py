import os
import sys
from dotenv import load_dotenv
from string import Template

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import get_filename_from_url
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

# logger = get_logger(TASK, log_dir=parent_folder / DATA_FOLDER/ "logs")

if __name__ == '__main__':
    
    file_name = get_filename_from_url(INDEX_MD_URL)
    index_md_file = parent_folder / DATA_FOLDER / file_name
    index_md_file.parent.mkdir(parents=True, exist_ok=True)
    if not index_md_file.exists():
        r = requests.get(INDEX_MD_URL) 
        with open(index_md_file, 'wb') as f:
            f.write(r.content)




