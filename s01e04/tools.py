import logging
from pathlib import Path
import sys
from langchain_core.tools import tool
import os
import requests
from langchain_core.callbacks import BaseCallbackHandler

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from libs.filetype_detect import detect_file_type
from libs.generic_helpers import read_file_base64, read_file_text, save_file

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
PARENT_FOLDER_PATH = Path(os.getenv("PARENT_FOLDER_PATH"))
PACKAGES_URL = os.getenv('POST_URL1')

@tool
def get_file_from_url(url: str, folder: Path) -> Path | None:
    """ Download a file from a URL and save it to the specified folder. Returns the path to the saved file."""
    return save_file(url, folder)

@tool
def get_file_list(folder: Path, filter: str = None) -> list[str]:
    """ Get a list of files in the specified folder, optionally filtered by a string .f.ex md. 
    No wildcards, just a simple substring match."""
    if filter:
        return [f for f in folder.glob(f"*{filter}*") if f.is_file()]
    return [f for f in folder.glob("*") if f.is_file()]

@tool
def read_file(file_path: Path | str) -> str:
    """ Read the contents of a file and returns as a strng. Text files are read as UTF-8, 
    binary files (targeted to images) are read and returned as base64-encoded string."""
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    info = detect_file_type(file_path)
    
    if info.final_kind == "text":
        return read_file_text(file_path)
    else:
        return read_file_base64(file_path)
    
# @tool
# def redirect_package(packageid: str, destination: str, code: str) -> dict:
#     """Redirect a package to a new destination using a security code provided by the operator.
#     Returns a confirmation code that must be passed back to the operator."""
#     payload = RedirectPackageRequest(
#         apikey=AI_DEVS_SECRET,
#         packageid=packageid,
#         destination=destination,
#         code=code,
#     )
#     response = requests.post(PACKAGES_URL, json=payload.model_dump())
#     return response.json()