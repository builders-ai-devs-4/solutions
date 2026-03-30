import os
import sys
from string import Template
from pathlib import Path
from dotenv import load_dotenv
import requests

parent_folder_path = Path(__file__).parent.parent
load_dotenv(parent_folder_path / ".env") 
sys.path.insert(0, str(parent_folder_path.parent)) 
sys.path.insert(0, str(Path(__file__).parent)) 
sys.path.insert(0, str(parent_folder_path)) 

load_dotenv()
from libs.generic_helpers import save_file
from libs.tomarkdown import extract_files_from_md, transform_html_to_markdown
from libs.database import Database

AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
SOLUTION_URL   = os.getenv('SOLUTION_URL')
DATA_FOLDER    = os.getenv('DATA_FOLDER')
TASK_NAME      = os.getenv('TASK_NAME')
AGENTIC_API_URL = os.getenv('AGENTIC_API_URL')
CSV_FILES_URL = os.getenv('SOURCE_URL1')

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
date_folder_path = parent_folder_path / DATA_FOLDER
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
db_dir_path = task_data_folder / "db"
csvs_dir_path = task_data_folder / "csvs"
os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)
os.environ["DATA_FOLDER_PATH"] = str(date_folder_path)
os.environ["DB_DIR_PATH"] = str(db_dir_path)
os.environ["CSVS_DIR_PATH"] = str(csvs_dir_path)
db_dir_path.mkdir(parents=True, exist_ok=True)
csvs_dir_path.mkdir(parents=True, exist_ok=True)
db_path = db_dir_path / "negotiations.db"

# os.environ["DB_PATH"] = str(db_path)

from libs.loggers import LoggerCallbackHandler, agent_logger

# from langfuse import Langfuse, get_client

# Singleton initialization of Langfuse (only once, at startup)
# This ensures that all agents and tools share the same Langfuse instance and configuration.

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
        agent_logger.info(f"[task] Downloading {filename} from {file_url}")
        save_file(file_url, csvs_dir_path, override=True)

if __name__ == "__main__":
    
    agent_logger.info(f"[task] Starting task: {TASK_NAME}")
    if not db_path.exists():
        md = transform_html_to_markdown(csvs_dir_path, CSV_FILES_URL)
        save_extracted_csv_files(CSV_FILES_URL, csvs_dir_path, md)
        
        with Database(db_path) as db:

            counts = db.load_csv_dir_multi_table(csvs_dir_path)

            # Sprawdź co jest w bazie
            agent_logger.info(f"Database tables: {db.tables()}")

            for table in db.tables():
                agent_logger.info(f"\n-- {table} --")
                for col in db.schema(table):
                    agent_logger.info(f"  {col['column_name']}: {col['column_type']}")


            
  