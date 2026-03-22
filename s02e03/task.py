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

FAILURE_LOG = os.getenv('SOURCE_URL1')

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
data_folder_path = parent_folder_path / DATA_FOLDER
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME

os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)
os.environ["DATA_FOLDER_PATH"] = str(data_folder_path)

WORKSPACE       = task_data_folder / "workspace"
SEVERITY_DIR    = WORKSPACE / "01_severity"
KEYWORDS_DIR    = WORKSPACE / "02_keywords"
CHUNKS_DIR      = WORKSPACE / "03_chunks"
COMPRESSED_DIR  = WORKSPACE / "04_compressed"

failure_log_template = Template(FAILURE_LOG)
failure_log_url = failure_log_template.substitute(ai_devs_secret=AI_DEVS_SECRET)
os.environ["FAILURE_LOG_URL"] = str(failure_log_url)

os.environ["WORKSPACE"] = str(WORKSPACE)
os.environ["SEVERITY_DIR"] = str(SEVERITY_DIR)
os.environ["KEYWORDS_DIR"] = str(KEYWORDS_DIR)
os.environ["CHUNKS_DIR"] = str(CHUNKS_DIR)
os.environ["COMPRESSED_DIR"] = str(COMPRESSED_DIR)

from loggers import LoggerCallbackHandler, agent_logger
from supervisor_agent import SUPERVISOR_CONFIG, supervisor

TOKEN_LIMIT = 1450
supervisor_user_template = (parent_folder_path/ "prompts" / "supervisor_user.md").read_text(encoding="utf-8")
supervisor_user = Template(supervisor_user_template).substitute(
    TOKEN_LIMIT=TOKEN_LIMIT,
    FAILURE_LOG_URL=failure_log_url,
    SOLUTION_URL=SOLUTION_URL,
    TASK_DATA_FOLDER_PATH=task_data_folder
    )

if __name__ == "__main__":
    
    
    agent_logger.info(f"[task] Starting task: {TASK_NAME}")
    result = supervisor.invoke(
        {"messages": [{"role": "user", "content": supervisor_user}]},
        config=SUPERVISOR_CONFIG,
    )
    agent_logger.info(f"[task] {result['messages'][-1].content}")
    