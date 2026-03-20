
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import os
import base64
import requests

def get_filename_from_url(url: str = None) -> str:
    if url is None:
        return None
    urlpath = urlsplit(url).path
    return os.path.basename(urlpath)

def get_path_from_url(url: str = None) -> str:
    if url is None:
        return None
    return urljoin(url, ".")


def save_file(file_url: str, folder: Path) -> Path:
    file_name = get_filename_from_url(file_url)
    index_md_file = folder / file_name
    index_md_file.parent.mkdir(parents=True, exist_ok=True)
    if not index_md_file.exists():
        r = requests.get(file_url) 
        with open(index_md_file, 'wb') as f:
            f.write(r.content)
    return index_md_file


def read_file_base64(file_path: Path | str) -> str:
    path = Path(file_path)
    with path.open("rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def read_file_text(file_path: Path | str) -> str:
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as f:
        return f.read()