import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from libs.generic_helpers import save_file
from libs.tomarkdown import extract_files_from_md, transform_html_to_markdown
from libs.database import Database

parent_folder_path = Path(__file__).parent.parent
load_dotenv(parent_folder_path / ".env") 
sys.path.insert(0, str(parent_folder_path.parent)) 
sys.path.insert(0, str(Path(__file__).parent)) 
sys.path.insert(0, str(parent_folder_path)) 

load_dotenv()

TASK_NAME      = os.getenv('TASK_NAME')
TASK_DATA_FOLDER_PATH = os.getenv("TASK_DATA_FOLDER_PATH")
PARENT_FOLDER_PATH = os.getenv("PARENT_FOLDER_PATH")    
DATA_FOLDER_PATH = os.getenv("DATA_FOLDER_PATH")
DB_DIR_PATH = os.getenv("DB_DIR_PATH")
CSVS_DIR_PATH = os.getenv("CSVS_DIR_PATH")

from libs.loggers import agent_logger

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


def creating_db(csvs_dir_path: Path | str, db_path: Path | str):
    with Database(db_path) as db:
        counts = db.load_csv_dir_multi_table(csvs_dir_path)
        agent_logger.info(f"Loaded CSV files into database. Row counts: {counts}")
        agent_logger.info(f"Database tables: {db.tables()}")

        for table in db.tables():
            agent_logger.info(f"\n-- {table} --")
            for col in db.schema(table):
                agent_logger.info(f"  {col['column_name']}")

def run_preparation(csv_files_url: str, csvs_dir_path: Path | str, db_path: Path | str):
    if not db_path.exists():
        agent_logger.info(f"[task] Database not found. Creating new database at {db_path}")
        md = transform_html_to_markdown(csvs_dir_path, csv_files_url)
        agent_logger.info(f"[task] Extracted markdown saved to {md}")
        save_extracted_csv_files(csv_files_url, csvs_dir_path, md)
        agent_logger.info(f"[task] CSV files extracted and saved to {csvs_dir_path}")
        creating_db(csvs_dir_path, db_path)
        agent_logger.info(f"[task] Database created at {db_path}")
