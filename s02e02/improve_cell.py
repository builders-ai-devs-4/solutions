import os
import sys
from dotenv import load_dotenv
from string import Template
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests

load_dotenv()
from modules.optimise_countur import check_edge_connectivity, enhance_lines, is_detection_confident, prepare_for_llm, preprocess_cell


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

from modules.grid_detector import save_img
name_img = 'cell_3_3'
cell = parent_folder_path / DATA_FOLDER / TASK_NAME / 'cells' / f'{name_img}.png'

preprocessed = preprocess_cell(cell)
save_img(task_data_folder / "cells" / f"{name_img}_preprocessed.png", preprocessed)
enhanced = enhance_lines(preprocessed)
save_img(task_data_folder / "cells" / f"{name_img}_enhanced.png", enhanced)
edge_connectivity = check_edge_connectivity(enhanced)
# detection_confident = is_detection_confident(edge_connectivity)
llm_ready = prepare_for_llm(enhanced)
save_img(task_data_folder / "cells" / f"{name_img}_llm_ready.png", llm_ready)