# oko_client.py — osobny moduł, importowany przez tools
import os
from bs4 import BeautifulSoup
import requests

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
OKO_URL     = os.getenv('OKO_URL')
HUB_URL        = os.getenv('HUB_URL')
LOGIN= os.getenv('LOGIN')
PASSWORD= os.getenv('PASSWORD')

from libs.loggers import agent_logger

_session: requests.Session | None = None

def get_oko_session() -> requests.Session:
    global _session
    if _session is not None:
        agent_logger.info("[get_oko_session] reusing existing session")
        return _session

    agent_logger.info("[get_oko_session] creating new session")
    _session = requests.Session()

    login_url = f"{OKO_URL}/"
    agent_logger.info(f"[get_oko_session] login_url={login_url} login={LOGIN}")

    resp = _session.post(login_url, data={
        "action": "login",
        "login": LOGIN,
        "password": PASSWORD,
        "access_key": AI_DEVS_SECRET,
    })

    agent_logger.info(
        f"[get_oko_session] login response status={resp.status_code} "
        f"contains_login_form={'login-form' in resp.text}"
    )

    if "login-form" in resp.text:
        raise RuntimeError("OKO login failed — check credentials/access_key")

    agent_logger.info("[get_oko_session] login successful")
    return _session
