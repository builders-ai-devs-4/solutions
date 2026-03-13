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
from agents import railway_agent


load_dotenv()
AI_DEVS_SECRET =  os.getenv('AI_DEVS_SECRET')
HUB_URL =  os.getenv('HUB_URL')
TASK =  os.getenv('TASK')
SOLUTION_URL =  os.getenv('SOLUTION_URL')
DATA_FOLDER =  os.getenv('DATA_FOLDER')
TASK_NAME =  os.getenv('TASK_NAME')
INIT_SESSION_ID =  os.getenv('INIT_SESSION_ID')
AGENTIC_API_URL = os.getenv('AGENTIC_API_URL')

current_folder = Path(__file__)
parent_folder = current_folder.parent

logger = get_logger(TASK, log_dir=parent_folder / DATA_FOLDER/ "logs_task")

if __name__ == "__main__":

    ans = {
        "apikey": AI_DEVS_SECRET,
        "task": TASK_NAME,
        "answer": {
            "action": "help"

        }
    }

    logger.info(f"Sending answer: {ans}")
    response = requests.post(SOLUTION_URL, json=ans)
    logger.info(f"Response status: {response.status_code}")
    logger.info(f"Response body: {response.text}")
    print(response.text)

    answer_file = parent_folder / DATA_FOLDER / 'answer.txt'

    with open(answer_file, 'wb') as f:
        f.write(response.content)
        
    result = railway_agent.invoke(
        {"messages": [{"role": "user", "content": "Activate route X-01 and find the flag."}]},
        config={"configurable": {"thread_id": "railway-1"}},
    )
    logger.info(result["messages"][-1].content)

