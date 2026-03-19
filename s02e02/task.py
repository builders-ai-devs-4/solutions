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
MAP = os.getenv('SOURCE_URL1')
MAP_RESET = os.getenv('SOURCE_URL2')

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
date_folder_path = parent_folder_path / DATA_FOLDER
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
# os.environ["DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)
os.environ["DATA_FOLDER_PATH"] = str(date_folder_path)

map_template = Template(MAP)
map_url = map_template.substitute(ai_devs_secret=AI_DEVS_SECRET)
os.environ["MAP_URL"] = str(map_url)

map_reset_template = Template(MAP_RESET)
map_reset_url = map_reset_template.substitute(ai_devs_secret=AI_DEVS_SECRET)
os.environ["MAP_RESET_URL"] = str(map_reset_url)

from tools import encode_prompt
from loggers import LoggerCallbackHandler, agent_logger
from supervisor_agent import SUPERVISOR_CONFIG, supervisor


if __name__ == "__main__":
    
    agent_logger.info(f"[task] Starting task: {TASK_NAME}")
    result = supervisor.invoke(
        {"messages": 
            [{"role": "user",
                "content" : (
                    f"Solve the 3x3 electrical wiring puzzle.\n"
                    f"Board URL: {map_url}\n"
                    f"Working folder: {task_data_folder}\n\n"
                    f"The board is a 3x3 grid of connector symbols. "
                    f"Your goal is to rotate cells until all three power stations "
                    f"(PWR6132PL, PWR1593PL, PWR7264PL) are powered from the emergency "
                    f"source on the left side of cell 3x1.\n\n"
                    f"You do NOT have any separate target image. The correct configuration "
                    f"is defined only by the wiring rules and by the server returning a "
                    f"flag {{FLG:...}} when the puzzle is solved.\n\n"
                    f"You have the following tools available: save_file_from_url, "
                    f"get_grid_cells_frome_image, classify_grid, rotate_cell, scan_flag, "
                    f"reset_map, get_file_list, read_file.\n\n"
                    f"Follow the system instructions carefully, analyse the current board, "
                    f"plan and execute rotations, re-classify after changes, and use "
                    f"reset_map() if your reasoning or classification seems inconsistent.\n"
                    f"Stop ONLY when you receive a flag from the server.\n\n"
                    f"Start now."
                )

              }]},
        config=SUPERVISOR_CONFIG,
    )
    agent_logger.info(f"[supervisor] {result['messages'][-1].content}")
    
save_file(map_url, task_data_folder, override=True)