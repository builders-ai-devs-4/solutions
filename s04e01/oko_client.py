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
OKO_URL     = os.getenv('OKO_URL').rstrip("/")
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

    s = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/146.0.0.0 Mobile Safari/537.36",
        "Referer": f"{OKO_URL}/",
        "Origin": OKO_URL,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                  "image/avif,image/webp,image/apng,*/*;q=0.8,"
                  "application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Upgrade-Insecure-Requests": "1",
    }

    data = {
        "action": "login",
        "login": LOGIN,
        "password": PASSWORD,
        "access_key": AI_DEVS_SECRET,
    }

    login_url = f"{OKO_URL}/"
    agent_logger.info(f"[get_oko_session] login_url={login_url} login={LOGIN}")

    resp = s.post(login_url, data=data, headers=headers)

    agent_logger.info(
        f"[get_oko_session] login response status={resp.status_code} "
        f"contains_login_form={'login-form' in resp.text}"
    )

    if "login-form" in resp.text:
        raise RuntimeError("OKO login failed — check credentials/access_key")

    agent_logger.info("[get_oko_session] login successful")
    _session = s
    return _session