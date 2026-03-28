import os
import sys
from unittest import result
from dotenv import load_dotenv
from string import Template

from database import SensorDatabase, create_db, insert_data, run_validation

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import extract_zip, get_filename_from_url, get_path_from_url, save_file

from pathlib import Path
import requests

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
TASK           = os.getenv('TASK')
SOLUTION_URL   = os.getenv('SOLUTION_URL')
DATA_FOLDER    = os.getenv('DATA_FOLDER')
TASK_NAME      = os.getenv('TASK_NAME')

SENSORS_ZIP_URL = os.getenv('SOURCE_URL1')

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
date_folder_path = parent_folder_path / DATA_FOLDER
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
sensors_dir_path = task_data_folder / "sensors"
db_dir_path = task_data_folder / "db"
os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)
os.environ["DATA_FOLDER_PATH"] = str(date_folder_path)
os.environ["SENSORS_DIR_PATH"] = str(sensors_dir_path)
os.environ["DB_DIR_PATH"] = str(db_dir_path)
db_dir_path.mkdir(parents=True, exist_ok=True)
db_path = db_dir_path / "sensors.db"
os.environ["DB_PATH"] = str(db_path)

# from seeker_agent import SEEKER_CONFIG, seeker
from libs.loggers import LoggerCallbackHandler, agent_logger

# seeker_user_template = (parent_folder_path/ "prompts" / "seeker_user.md").read_text(encoding="utf-8")
# seeker_user = Template(seeker_user_template).substitute(
#     PWR_ID_CODE=PWR_ID_CODE,
#     DRONE_MAP_URL=drone_map_url,
#     DRONE_DOCS_URL=DRONE_DOCS_URL,
#     MAP_FOLDER_PATH=map_folder_path,
#     DOCS_FOLDER_PATH=docs_folder_path,  
#     SOLUTION_URL=SOLUTION_URL,
#     )


if __name__ == "__main__":
    
    agent_logger.info(f"[task] Starting task: {TASK_NAME}")
    

    
    if not db_path.exists():
        
        db_path = create_db(db_path)
        agent_logger.info(f"[task] Created database at {db_path}")
    
        filename_from_url = get_filename_from_url(SENSORS_ZIP_URL)
        agent_logger.info(f"[task] Downloading sensors data from {SENSORS_ZIP_URL} to {sensors_dir_path}")
        sensors_dir_path.mkdir(parents=True, exist_ok=True)
        zip_file_path = save_file(SENSORS_ZIP_URL, sensors_dir_path, override=True)
        extracted_dir_path = sensors_dir_path / 'extracted'
        extracted_dir_path.mkdir(parents=True, exist_ok=True)
        extract_zip(zip_file_path, extracted_dir_path)
        agent_logger.info(f"[task] Extracting {zip_file_path} to {extracted_dir_path}")

        result = insert_data(db_path, extracted_dir_path)
        print(result[["sensor_type", "temperature_K", "filename"]])
        
        with SensorDatabase(db_path) as db:
            db.insert_data(extracted_dir_path)
            
            readings  = db.load_readings()
            results   = run_validation(readings)
            anomalies = [r for r in results if r.is_anomaly]
            agent_logger.info(f"[task] Validation completed. Found {len(anomalies)} anomalies")    
    
    result = seeker.invoke(
        {"messages": [{"role": "user", "content": seeker_user}]},
        config=SEEKER_CONFIG,
    )
    agent_logger.info(f"[task] {result['messages'][-1].content}")
    
    
  