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

from tools import encode_prompt

logger = get_logger(TASK, log_dir=parent_folder_path / DATA_FOLDER / "logs_task")


categorize_template = Template(CATEGORIZE)
categorize_url = categorize_template.substitute(ai_devs_secret=AI_DEVS_SECRET)

if __name__ == "__main__":
    
    prompt = "Serce rośnie, patrząc na to, jak Oskar radzi sobie w lidze portugalskiej. Czujemy dumę, patrząc na Oskara. Mogliśmy dostać za niego wyższą kwotę odstępnego, sprzedając do innego klubu, ale nie wiadomo, czy grałby np. w Anglii."
 
    logger.info(f"Getting csv data from: {categorize_url}")
    tokens, num_tokens = encode_prompt(prompt, "gpt-5-mini")
    categorize_filename = get_path_from_url(categorize_url)
    save_file(categorize_url, task_data_folder, override=True)
    # logger.info(f"Saved csv data to: {task_data_folder / categorize_filename}")
    
    # ans = {
    #     "apikey": AI_DEVS_SECRET,
    #     "task": TASK_NAME,
    #     "answer": {
    #         "prompt": prompt

    #     }
    # }

    # logger.info(f"Sending answer: {ans}")
    # response = requests.post(SOLUTION_URL, json=ans)
    # logger.info(f"Response status: {response.status_code}")
    # logger.info(f"Response body: {response.text}")
    # print(response.text)

    # answer_file = task_data_folder / 'answer.txt'

    # with open(answer_file, 'wb') as f:
    #     f.write(response.content)
        