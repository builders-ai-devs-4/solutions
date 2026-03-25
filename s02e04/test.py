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

MAILBOX_HELP_URL= os.getenv('SOURCE_URL1')

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
date_folder_path = parent_folder_path / DATA_FOLDER
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME

os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)
os.environ["DATA_FOLDER_PATH"] = str(date_folder_path)
os.environ["MAILBOX_HELP_URL"] = str(MAILBOX_HELP_URL)


from loggers import LoggerCallbackHandler, agent_logger

if __name__ == "__main__":
    
    ans = {
        "apikey": AI_DEVS_SECRET,
        "action": "help",
        "page": 1
    
    }
        
    agent_logger.info(f"[task] Starting task: {TASK_NAME}")
    agent_logger.info(f"Help: {ans ['action']} | Page: {ans['page']}")
    
    response = requests.post(
        MAILBOX_HELP_URL,
        json=ans
    )
    agent_logger.info(f"Response status code: {response.status_code}")
    agent_logger.info(f"Response content: {response.content}")
    agent_logger.info(f"Response text: {response.text}")
    
    ans = {
        "apikey": AI_DEVS_SECRET,
        "action": "getInbox",
        "page": 1
        
    }
        
    agent_logger.info(f"[task] Starting task: {TASK_NAME}")
    agent_logger.info(f"Help: {ans['action']} | Page: {ans['page']}")
    
    response = requests.post(
        MAILBOX_HELP_URL,
        json=ans
    )
    agent_logger.info(f"Response status code: {response.status_code}")
    agent_logger.info(f"Response content: {response.content}")
    agent_logger.info(f"Response text: {response.text}")
    
    ans = {
        "apikey": AI_DEVS_SECRET,
        "action": "getMessages",
        "ids": [5,"7dd1e966faa1fe536e36bc12c25e864f"]
    }
        
    agent_logger.info(f"[task] Starting task: {TASK_NAME}")
    agent_logger.info(f"Help: {ans['action']} | IDs: {ans['ids']}")
    
    response = requests.post(
        MAILBOX_HELP_URL,
        json=ans
    )
    agent_logger.info(f"Response status code: {response.status_code}")
    agent_logger.info(f"Response content: {response.content}")
    agent_logger.info(f"Response text: {response.text}")

    ans = {
        "apikey": AI_DEVS_SECRET,
        "action": "getInbox",
    }
    
    agent_logger.info(f"[task] Starting task: {TASK_NAME}")
    agent_logger.info(f"Help: {ans['action']} | Page: {ans.get('page', 'N/A')}")
    
    response = requests.post(
        MAILBOX_HELP_URL,
        json=ans
    )
    agent_logger.info(f"Response status code: {response.status_code}")
    agent_logger.info(f"Response content: {response.content}")
    agent_logger.info(f"Response text: {response.text}")
    