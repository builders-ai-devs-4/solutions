# oko_client.py — osobny moduł, importowany przez tools
import os
import requests

LOGIN= os.getenv('LOGIN')
PASSWORD= os.getenv('PASSWORD')
AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
OKO_URL     = os.getenv('OKO_URL')

_session: requests.Session | None = None

def get_oko_session() -> requests.Session:
    global _session
    if _session is not None:
        return _session

    _session = requests.Session()
    resp = _session.post(f"{OKO_URL}/", data={
        "action":     "login",
        "login":      LOGIN,
        "password":   PASSWORD,
        "access_key": AI_DEVS_SECRET,
    })
    if "login-form" in resp.text:
        raise RuntimeError("OKO login failed — check credentials/access_key")
    return _session