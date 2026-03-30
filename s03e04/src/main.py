
import os
import sys
from string import Template
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
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

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
data_folder_path = parent_folder_path / DATA_FOLDER
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME
db_dir_path = task_data_folder / "db"
csvs_dir_path = task_data_folder / "csvs"
os.environ["TASK_DATA_FOLDER_PATH"] = str(task_data_folder)
os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)
os.environ["DATA_FOLDER_PATH"] = str(data_folder_path)
os.environ["DB_DIR_PATH"] = str(db_dir_path)
os.environ["CSVS_DIR_PATH"] = str(csvs_dir_path)
db_dir_path.mkdir(parents=True, exist_ok=True)
csvs_dir_path.mkdir(parents=True, exist_ok=True)
db_path = db_dir_path / "negotiations.db"
os.environ["DB_PATH"] = str(db_path)

from libs.loggers import LoggerCallbackHandler, agent_logger
from resources.preparation import run_preparation
from modules.seeker_agent import seeker, SEEKER_CONFIG
MODULE_NAME = "api-main"
run_preparation(CSV_FILES_URL, csvs_dir_path, db_path)

from langfuse import Langfuse, get_client

# Singleton initialization of Langfuse (only once, at startup)
# This ensures that all agents and tools share the same Langfuse instance and configuration.

Langfuse(
    public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
    secret_key=os.environ["LANGFUSE_SECRET_KEY"],
)

app = FastAPI()

agent_logger.info(f"[{MODULE_NAME}] Api server started. Listening for requests...")
agent_logger.info(f"[{MODULE_NAME}] task_data_folder={task_data_folder}")
agent_logger.info(f"[{MODULE_NAME}] data_folder_path={data_folder_path}")
agent_logger.info(f"[{MODULE_NAME}] parent_folder_path={parent_folder_path}")
agent_logger.info(f"[{MODULE_NAME}] db_path={db_path}")
agent_logger.info(f"[{MODULE_NAME}] csvs_dir_path={csvs_dir_path}")


@app.get("/")
async def health_check():
    agent_logger.info(f"[{MODULE_NAME}] Health check received")
    agent_logger.info(f"[{MODULE_NAME}] Response={'status': 'ok'}")
    return {"status": "ok"}

@app.post("/", response_model=ResponseToOperator)
async def root_post(req: OperatorsRequest):
    api_logger.info(f"POST / | session={req.sessionID} | msg={req.msg!r}")
    answer = await run_agent(req.sessionID, req.msg)
    api_logger.debug(f"POST / | session={req.sessionID} | response={answer!r}")
    return ResponseToOperator(msg=answer)




