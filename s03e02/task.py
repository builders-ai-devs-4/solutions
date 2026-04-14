import os
import sys
from dotenv import load_dotenv
from string import Template
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()
AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
SOLUTION_URL   = os.getenv('SOLUTION_URL')
SHELL_URL      = os.getenv('SOURCE_URL1')
DATA_FOLDER    = os.getenv('DATA_FOLDER')
TASK_NAME      = os.getenv('TASK_NAME')

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
date_folder_path = parent_folder_path / DATA_FOLDER
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
task_data_folder.mkdir(parents=True, exist_ok=True)
os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)
os.environ["DATA_FOLDER_PATH"] = str(date_folder_path)

os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"]    = str(parent_folder_path)
os.environ["SHELL_URL"]             = SHELL_URL

from libs.loggers import LoggerCallbackHandler, agent_logger
from seeker_agent import SEEKER_CONFIG, seeker

seeker_user_template = (parent_folder_path / "prompts" / "seeker_user.md").read_text(encoding="utf-8")
seeker_user = Template(seeker_user_template).substitute(
    SHELL_URL=SHELL_URL,
    SOLUTION_URL=SOLUTION_URL,
)

if __name__ == "__main__":
    agent_logger.info(f"[task] Starting task: {TASK_NAME}")
    result = seeker.invoke(
        {"messages": [{"role": "user", "content": seeker_user}]},
        config=SEEKER_CONFIG,
    )
    agent_logger.info(f"[task] {result['messages'][-1].content}")
