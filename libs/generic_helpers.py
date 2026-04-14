
import csv
from pathlib import Path
from typing import Any, Iterator
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

def save_file(file_url: str, folder: Path | str, override: bool = False) -> Path:
    file_name = get_filename_from_url(file_url)
    index_md_file = Path(folder) / file_name
    index_md_file.parent.mkdir(parents=True, exist_ok=True)
    if not index_md_file.exists() or override:
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


def read_csv_row(csv_file: Path) -> Iterator[dict[str, Any]]:
    with csv_file.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            row = row.copy()  
            yield row

def read_csv_rows(file_path: Path) -> list[dict]:
    """Read a CSV file and return list of dicts with all columns as keys."""
    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)
