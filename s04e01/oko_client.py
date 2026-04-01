# oko_client.py — osobny moduł, importowany przez tools
import os
from bs4 import BeautifulSoup
import requests


TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
HUB_URL        = os.getenv('HUB_URL')

OKO_URL     = os.getenv('OKO_URL').rstrip("/")
LOGIN = os.environ.get("LOGIN")
PASSWORD = os.environ.get("PASSWORD")
AI_DEVS_SECRET = os.environ.get("AI_DEVS_SECRET")

from libs.loggers import LoggerCallbackHandler, agent_logger

_session: requests.Session | None = None


def reset_oko_session() -> None:
    global _session
    if _session is not None:
        try:
            _session.cookies.clear()
        except Exception as e:
            agent_logger.warning(f"[reset_oko_session] cookies.clear failed: {e!r}")

        try:
            _session.close()
        except Exception as e:
            agent_logger.warning(f"[reset_oko_session] session.close failed: {e!r}")

    _session = None
    agent_logger.info("[reset_oko_session] session cache cleared")


def get_oko_session() -> requests.Session:
    global _session
    if _session is not None:
        agent_logger.info("[get_oko_session] reusing existing session")
        return _session

    agent_logger.info(
        f"[get_oko_session] credentials present "
        f"login_set={bool(LOGIN)} password_set={bool(PASSWORD)} secret_set={bool(AI_DEVS_SECRET)}"
    )
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

    resp = s.post(login_url, data=data, headers=headers, allow_redirects=False)

    agent_logger.info(
        f"[get_oko_session] login response status={resp.status_code} "
        f"location={resp.headers.get('Location')} "
        f"contains_login_form={'login-form' in resp.text}"
    )
    agent_logger.info(f"[get_oko_session] set-cookie={resp.headers.get('Set-Cookie')}")

    if "login-form" in resp.text:
        try:
            s.close()
        except Exception:
            pass
        raise RuntimeError("OKO login failed — check credentials/access_key")

    agent_logger.info("[get_oko_session] login successful")
    _session = s
    return _session