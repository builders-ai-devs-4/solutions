import os
import sys
from string import Template
from pathlib import Path
from dotenv import load_dotenv

from libs.generic_helpers import save_file
from libs.tomarkdown import extract_files_from_md

parent_folder_path = Path(__file__).parent.parent
load_dotenv(parent_folder_path / ".env") 
sys.path.insert(0, str(parent_folder_path.parent)) 
sys.path.insert(0, str(Path(__file__).parent)) 

import requests

parent_folder_path = Path(__file__).parent.parent
load_dotenv(parent_folder_path / ".env") 
sys.path.insert(0, str(parent_folder_path.parent)) 
sys.path.insert(0, str(Path(__file__).parent)) 
sys.path.insert(0, str(parent_folder_path)) 

load_dotenv()

AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
SOLUTION_URL   = os.getenv('SOLUTION_URL')
DATA_FOLDER    = os.getenv('DATA_FOLDER')
TASK_NAME      = os.getenv('TASK_NAME')
AGENTIC_API_URL = os.getenv('AGENTIC_API_URL')
CSV_FILES_URL = os.getenv('SOURCE_URL1')
TASK_DATA_FOLDER_PATH = os.getenv("TASK_DATA_FOLDER_PATH")
PARENT_FOLDER_PATH = os.getenv("PARENT_FOLDER_PATH")    
DATA_FOLDER_PATH = os.getenv("DATA_FOLDER_PATH")
DB_DIR_PATH = os.getenv("DB_DIR_PATH")
CSVS_DIR_PATH = os.getenv("CSVS_DIR_PATH")

from libs.loggers import LoggerCallbackHandler, agent_logger

MODULE_NAME = "preparation"

def save_extracted_csv_files(csv_files_url: str, csvs_dir_path: Path | str, md: Path | str):
    md = Path(md)
    csvs_dir_path = Path(csvs_dir_path)
    files = extract_files_from_md(
            md.read_text(encoding='utf-8'),
            base_url=csv_files_url,
            extensions=[".csv"]
        )
    for file_info in files:
        file_url = file_info["url"]
        filename = file_info["name"]
        agent_logger.info(f"[{MODULE_NAME}] Downloading {filename} from {file_url}")
        save_file(file_url, csvs_dir_path, override=True)

