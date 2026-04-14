
import csv
import json
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urljoin, urlsplit
import os
import base64
import requests

import zipfile

def get_filename_from_url(url: str = None) -> str:
    if url is None:
        return None
    urlpath = urlsplit(url).path
    return os.path.basename(urlpath)

def get_path_from_url(url: str = None) -> str:
    if url is None:
        return None
    return urljoin(url, ".")

def save_file(file_url: str, folder: Path | str, override: bool = False, prefix: str = "", suffix: str = "") -> Path:
    file_name = get_filename_from_url(file_url)
    org_log = Path(file_name)
    if prefix:
        file_name = f"{prefix}_{org_log.stem}{org_log.suffix}"
    if suffix:
        file_name = f"{org_log.stem}_{suffix}{org_log.suffix}"
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

def save_text_file(path: str | Path, content: str, override: bool = True) -> Path:
    """Zapisuje string do pliku tekstowego. Tworzy foldery jeśli nie istnieją."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists() or override:
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
    return p


def read_json_files(folder: str, pattern: str = "*.json") -> list[dict]:
    """Wczytuje wszystkie pliki .json z folderu pasujące do wzorca.
    Zwraca listę słowników posortowaną po nazwie pliku."""
    folder_path = Path(folder)
    files = sorted(folder_path.glob(pattern))
    result = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            result.append({"file": str(f), "data": json.load(fh)})
    return result

def read_json_file(file_path: str | Path) -> dict:
    """Wczytuje pojedynczy plik .json i zwraca jego zawartość jako słownik."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json_file(file_path: str | Path, data: dict, append: bool = True) -> Path:
    """Zapisuje słownik do pliku .json. Tworzy foldery jeśli nie istnieją."""
    path = Path(file_path)
    if append and path.is_file():
        existing_data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(existing_data, list):
            existing_data.append(data)
        elif isinstance(existing_data, dict):
            existing_data.update(data)
        data = existing_data
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")
    return path


def extract_zip(
    zip_path: str,
    destination_dir: str,
    password: str | None = None
) -> bool:
    os.makedirs(destination_dir, exist_ok=True)

    pwd_bytes = password.encode("utf-8") if password else None

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(path=destination_dir, pwd=pwd_bytes)
        return True
    except zipfile.BadZipFile:
        print(f"Error: '{zip_path}' is not a valid ZIP file.")
    except RuntimeError as e:
        # Wrong password or missing password for an encrypted archive
        print(f"Encryption error: {e}")
    except FileNotFoundError:
        print(f"Error: file '{zip_path}' does not exist.")

    return False