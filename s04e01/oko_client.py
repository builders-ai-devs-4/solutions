# oko_client.py — osobny moduł, importowany przez tools
import os
import requests

_session: requests.Session | None = None

def get_oko_session() -> requests.Session:
    global _session
    if _session is not None:
        return _session

    _session = requests.Session()
    resp = _session.post("https://oko.ag3nts.org/", data={
        "action":     "login",
        "login":      os.environ["OKO_LOGIN"],
        "password":   os.environ["OKO_PASSWORD"],
        "access_key": os.environ["AI_DEVS_SECRET"],
    })
    if "login-form" in resp.text:
        raise RuntimeError("OKO login failed — check credentials/access_key")
    return _session