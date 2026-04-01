# oko_client.py — osobny moduł, importowany przez tools
import os
from bs4 import BeautifulSoup
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

    s = requests.Session()

    login_page = s.get(f"{OKO_URL}/")
    soup = BeautifulSoup(login_page.text, "html.parser")
    form = soup.find("form", class_="login-form")

    form_data = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        form_data[name] = inp.get("value", "")

    form_data["login"] = LOGIN
    form_data["password"] = PASSWORD
    form_data["access_key"] = AI_DEVS_SECRET

    resp = s.post(f"{OKO_URL}/", data=form_data)

    if "login-form" in resp.text:
        raise RuntimeError("OKO login failed — check credentials/access_key")

    _session = s
    return _session

