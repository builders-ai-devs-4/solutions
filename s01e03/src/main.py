import sys, os
from fastapi import FastAPI
from pathlib import Path

from dotenv import load_dotenv
parent_folder_path = Path(__file__).parent.parent
load_dotenv(parent_folder_path / ".env") 
sys.path.insert(0, str(parent_folder_path.parent)) 
sys.path.insert(0, str(Path(__file__).parent)) 

os.environ["PARENT_FOLDER_PATH"] = str(parent_folder_path)

from models.api_models import OperatorsRequest, ResponseToOperator
from task.agent import run_agent

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AI_DEVS_SECRET =  os.getenv('AI_DEVS_SECRET')
HUB_URL =  os.getenv('HUB_URL')
TASK =  os.getenv('TASK')
SOLUTION_URL =  os.getenv('SOLUTION_URL')
DATA_FOLDER =  os.getenv('DATA_FOLDER')
TASK_NAME =  os.getenv('TASK_NAME')
PACKAGES_URL = os.getenv('POST_URL1')

data_folder_path = parent_folder_path / DATA_FOLDER
os.environ["DATA_FOLDER_PATH"] = str(data_folder_path)

from models.api_models import OperatorsRequest, ResponseToOperator
from task.agent import run_agent
from task.loggers import api_logger

app = FastAPI()

@app.get("/")
async def health_check():
    return {"status": "ok"}

@app.post("/", response_model=ResponseToOperator)
async def root_post(req: OperatorsRequest):
    api_logger.info(f"POST / | session={req.sessionID} | msg={req.msg!r}")
    answer = await run_agent(req.sessionID, req.msg)
    api_logger.debug(f"POST / | session={req.sessionID} | response={answer!r}")
    return ResponseToOperator(msg=answer)
