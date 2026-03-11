from pathlib import Path
from langchain_core.tools import tool
from ..models.api_models import CheckPackageRequest, RedirectPackageResponse
import os
import requests

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
PARENT_FOLDER_PATH = Path(os.getenv("PARENT_FOLDER_PATH"))
PACKAGES_URL = os.getenv('POST_URL1')

@tool
def check_package(packageid: str):
    """Check the status of a package by its ID."""
    payload = CheckPackageRequest(apikey=AI_DEVS_SECRET, packageid=packageid)
    response = requests.post(PACKAGES_URL, json=payload.model_dump())
    return response.json()

@tool
def redirect_package(packageid: str, destination: str, code: str):
    # ... przekieruj paczkę ...
    return True