import os
import sys
from dotenv import load_dotenv
from string import Template

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
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

from agents import railway_agent 

current_folder = Path(__file__)
parent_folder  = current_folder.parent

logger = get_logger(TASK, log_dir=parent_folder / DATA_FOLDER / "logs_task")

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

