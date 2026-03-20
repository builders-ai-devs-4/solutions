import os
import sys
from dotenv import load_dotenv
from string import Template

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import get_path_from_url, save_file
from libs.logger import get_logger

from pathlib import Path
import requests
import json

COLLECT_ASSTS = False

current_folder = Path(__file__)
parent_folder_path = current_folder.parent
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)
load_dotenv()


OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AI_DEVS_SECRET =  os.getenv('AI_DEVS_SECRET')
HUB_URL =  os.getenv('HUB_URL')
TASK =  os.getenv('TASK')
SOLUTION_URL =  os.getenv('SOLUTION_URL')
INDEX_MD_URL =  os.getenv('SOURCE_URL1')
DATA_FOLDER =  os.getenv('DATA_FOLDER')
TASK_NAME =  os.getenv('TASK_NAME')


task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
os.environ["DATA_FOLDER_PATH"] = str(task_data_folder)

import json
from agents import asset_collector_agent, agent_logger, _RECURSION_LIMIT, build_memory_index, fill_form, DeclarationForm
from tools import LoggerCallbackHandler

url_folder = get_path_from_url(INDEX_MD_URL)
    
app_logger = get_logger(
    "app.s01e04",
    log_dir=task_data_folder / "logs",
    log_stem="task",
)

if __name__ == '__main__':
    if COLLECT_ASSTS:
        app_logger.info("Starting asset_collector_agent")
        result = asset_collector_agent.invoke(
            {
                "messages": [{
                    "role": "user",
                    "content": (
                        f"index_md_url: {INDEX_MD_URL}\n"
                        f"save_folder: {task_data_folder}\n"
                        f"base_url: {url_folder}"
                    )
                }]
            },
            config={
                "configurable": {"thread_id": "asset-collector-1"},
                "callbacks": [LoggerCallbackHandler(agent_logger)],
                "recursion_limit": _RECURSION_LIMIT,
            },
        )
        app_logger.info("Agent finished")
        app_logger.info(result["messages"][-1].content)
    
    app_logger.info("Starting memory builder")
    index_path = task_data_folder / "index.json"
    build_memory_index(task_data_folder, index_path)
    app_logger.info("Memory index complete")

    app_logger.info("Starting react_agent to fill the form")
    form: DeclarationForm = fill_form(index_path, shipment={
    "sender": "450202122",
    "origin": "Gdańsk",
    "destination": "Żarnowiec",
    "weight_kg": 2800,
    "budget_pp": 0,
    "contents": "kasety z paliwem do reaktora",
    "special_notes": "Brak",
    })
    app_logger.info(f"Form:\n{form.declaration}")

    app_logger.info("Submitting answer to hub")
    
    
    ans = {
        "apikey": AI_DEVS_SECRET,
        "task": TASK_NAME,
        "answer": {
            "declaration": form.declaration,
        }
        
    }
    response = requests.post(
        SOLUTION_URL,
        json=ans,
    )
    
    app_logger.info(f"Hub response: {response.status_code} {response.text}")
    print(response.text)

    answer_file = parent_folder_path / DATA_FOLDER / 'answer.txt'

    with open(answer_file, 'wb') as f:
        f.write(response.content)