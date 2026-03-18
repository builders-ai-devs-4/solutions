import cv2

import os
import sys
from dotenv import load_dotenv
from string import Template

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import get_path_from_url, save_file
from libs.logger import get_logger
# os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR\tessdata'
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
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
os.environ["DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)

map_template = Template(MAP)
map_url = map_template.substitute(ai_devs_secret=AI_DEVS_SECRET)
os.environ["MAP_URL"] = str(map_url)

map_reset_template = Template(MAP_RESET)
map_reset_url = map_reset_template.substitute(ai_devs_secret=AI_DEVS_SECRET)
os.environ["MAP_RESET_URL"] = str(map_reset_url)

INPUT_PATH =  str(task_data_folder / "solved_electricity.png")

img  = cv2.imread(INPUT_PATH)

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

roi = gray[88:379, 140:431]   # <-- nowe współrzędne

adapt = cv2.adaptiveThreshold(
    roi,
    maxValue       = 255,
    adaptiveMethod = cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    thresholdType  = cv2.THRESH_BINARY_INV,  # <-- INV zamiast BINARY
    blockSize      = 51,
    C              = 8
)
result = cv2.bitwise_not(adapt)
cv2.imwrite(str(task_data_folder / "maze_binary.jpg"), result)
    
# gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# roi = gray[99:386, 237:524]  # wytnij siatkę

# adapt = cv2.adaptiveThreshold(
#     roi,
#     maxValue   = 255,
#     adaptiveMethod = cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#     thresholdType  = cv2.THRESH_BINARY,
#     blockSize = 51,   # musi być NIEPARZYSTE; ~50% rozmiaru komórki (~95px)
#     C         = 8     # odjęcie od średniej – im wyższe, tym mniej białych px
# )

# # Negatyw = białe ścieżki na czarnym tle (lepsze do findContours)
# result = cv2.bitwise_not(adapt)
# cv2.imwrite(str(task_data_folder / "maze_binary.jpg"), result)