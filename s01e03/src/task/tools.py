import logging
from pathlib import Path
from langchain_core.tools import tool
from models.api_models import CheckPackageRequest, RedirectPackageRequest
import os
import requests
from langchain_core.callbacks import BaseCallbackHandler

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
PARENT_FOLDER_PATH = Path(os.getenv("PARENT_FOLDER_PATH"))
PACKAGES_URL = os.getenv('POST_URL1')

@tool
def check_package(packageid: str) -> dict:
    """Check the status and location of a package by its ID."""
    payload = CheckPackageRequest(apikey=AI_DEVS_SECRET, packageid=packageid)
    response = requests.post(PACKAGES_URL, json=payload.model_dump())
    return response.json()

@tool
def redirect_package(packageid: str, destination: str, code: str) -> dict:
    """Redirect a package to a new destination using a security code provided by the operator.
    Returns a confirmation code that must be passed back to the operator."""
    payload = RedirectPackageRequest(
        apikey=AI_DEVS_SECRET,
        packageid=packageid,
        destination=destination,
        code=code,
    )
    response = requests.post(PACKAGES_URL, json=payload.model_dump())
    return response.json()