import os
import sys
from dotenv import load_dotenv
from string import Template


from seeker_agent import SEEKER_CONFIG, seeker

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

MAILBOX_URL= os.getenv('SOURCE_URL1')

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
date_folder_path = parent_folder_path / DATA_FOLDER
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
mailbox_help_dir = task_data_folder / "mailbox_help"

os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)
os.environ["DATA_FOLDER_PATH"] = str(date_folder_path)
os.environ["MAILBOX_URL"] = str(MAILBOX_URL)
os.environ["MAILBOX_HELP_DIR"] = str(mailbox_help_dir)


from loggers import LoggerCallbackHandler, agent_logger

supervisor_user_template = (parent_folder_path/ "prompts" / "supervisor_user.md").read_text(encoding="utf-8")
supervisor_user = Template(supervisor_user_template).substitute(
    MAILBOX_HELP_DIR=mailbox_help_dir,
    MAILBOX_URL=MAILBOX_URL,
    SOLUTION_URL=SOLUTION_URL,
    TASK_DATA_FOLDER_PATH=task_data_folder,
    )

if __name__ == "__main__":
    
    agent_logger.info(f"[task] Starting task: {TASK_NAME}")
    result = seeker.invoke(
        {"messages": [{"role": "user", "content": supervisor_user}]},
        config=SEEKER_CONFIG,
    )
    agent_logger.info(f"[task] {result['messages'][-1].content}")
    
    