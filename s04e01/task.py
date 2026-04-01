import os
import sys
from dotenv import load_dotenv
from string import Template
from pathlib import Path

import requests
from langfuse.langchain import CallbackHandler

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
MODULE_NAME = "task"

load_dotenv()
AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
SOLUTION_URL   = os.getenv('SOLUTION_URL')
TOOLSEARCH_URL = os.getenv('SOURCE_URL1')
DATA_FOLDER    = os.getenv('DATA_FOLDER')
TASK_NAME      = os.getenv('TASK_NAME')
TASK_NAME      = os.getenv('TASK_NAME')
HUB_URL        = os.getenv('HUB_URL')

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
date_folder_path = parent_folder_path / DATA_FOLDER
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
task_data_folder.mkdir(parents=True, exist_ok=True)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)
os.environ["DATA_FOLDER_PATH"] = str(date_folder_path)
os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["TOOLSEARCH_URL"] = str(TOOLSEARCH_URL)

from libs.loggers import LoggerCallbackHandler, agent_logger
# from supervisor_agent import SUPERVISOR_CONFIG, supervisor
from langfuse import Langfuse, get_client

# Singleton initialization of Langfuse (only once, at startup)
# This ensures that all agents and tools share the same Langfuse instance and configuration.

Langfuse(
    public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
    secret_key=os.environ["LANGFUSE_SECRET_KEY"],
)

# supervisor_user_template = (parent_folder_path / "prompts" / "supervisor_user.md").read_text(encoding="utf-8")
# supervisor_user = Template(supervisor_user_template).substitute(
#     SOLUTION_URL=SOLUTION_URL,
# )

if __name__ == "__main__":
    
    agent_logger.info(f"[{MODULE_NAME}] Starting task: {TASK_NAME}")
    
    # try:
    #     result = supervisor.invoke(
    #         {"messages": [{"role": "user", "content": supervisor_user}]},
    #         config=SUPERVISOR_CONFIG,
    #     )
    # except Exception as e:
    #     agent_logger.error(f"[{MODULE_NAME}] Unhandled error: {e}")
    #     raise
    # finally:
    #     get_client().flush() # Ensure all logs are sent to Langfuse before exiting.
    # agent_logger.info(f"[{MODULE_NAME}] {result['messages'][-1].content}")

    ans = dict()
    ans["task"] = TASK_NAME
    ans["apikey"] = AI_DEVS_SECRET
    ans["answer"] = {'action': 'help'}
    response = requests.post(SOLUTION_URL, json=ans)


    agent_logger.info(f"[{MODULE_NAME}] {response.text}")

