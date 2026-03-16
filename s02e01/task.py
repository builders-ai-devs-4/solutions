import os
import sys
from dotenv import load_dotenv
from string import Template

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import get_path_from_url, save_file
from libs.logger import get_logger

from pathlib import Path
import requests

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
TASK           = os.getenv('TASK')
SOLUTION_URL   = os.getenv('SOLUTION_URL')
DATA_FOLDER    = os.getenv('DATA_FOLDER')
TASK_NAME      = os.getenv('TASK_NAME')
CATEGORIZE = os.getenv('SOURCE_URL1')


current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
os.environ["DATA_FOLDER_PATH"] = str(task_data_folder)

logger = get_logger(TASK, log_dir=parent_folder_path / DATA_FOLDER / "logs_task")

if __name__ == "__main__":
    
    categorize_filename = get_path_from_url(CATEGORIZE)
    save_file(CATEGORIZE, task_data_folder)
    
    ans = {
        "apikey": AI_DEVS_SECRET,
        "task": TASK_NAME,
        "answer": {
            "prompt": "prompt content"

        }
    }

    logger.info(f"Sending answer: {ans}")
    response = requests.post(SOLUTION_URL, json=ans)
    logger.info(f"Response status: {response.status_code}")
    logger.info(f"Response body: {response.text}")
    print(response.text)

    answer_file = task_data_folder / 'answer.txt'

    with open(answer_file, 'wb') as f:
        f.write(response.content)
        