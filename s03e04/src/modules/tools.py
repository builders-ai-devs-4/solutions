import os
import re
import sys
import time
from typing import Optional
from pathlib import Path
from duckdb import values
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
parent_folder_path = Path(__file__).parent.parent
sys.path.insert(0, str(parent_folder_path.parent)) 
sys.path.insert(0, str(Path(__file__).parent)) 
sys.path.insert(0, str(parent_folder_path)) 

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
DB_PATH = os.environ["DB_PATH"]

MAX_TOOL_ITERATIONS = 20
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 10 + 2  # 202
from libs.database import Database
from libs.loggers import agent_logger

@tool
def search_items(keyword: str) -> str:
    """Search items in the database by keyword.
    Returns matching item names and their codes.
    Use this first to find the item code before looking up cities."""
    with Database(Path(DB_PATH)) as db:
        rows = db.query_params(
            "SELECT name, code FROM items WHERE name ILIKE ? LIMIT 20",
            [f"%{keyword}%"]
        )
    if not rows:
        return "No items found."
    return "\n".join(f"{r['name']} ({r['code']})" for r in rows)


@tool
def get_cities_for_item(item_code: str) -> str:
    """Get all city names that have a specific item available, by item code.
    Returns a comma-separated list of city names."""
    with Database(Path(DB_PATH)) as db:
        rows = db.query_params(
            """
            SELECT DISTINCT c.name FROM cities c
            JOIN connections conn ON c.code = conn.cityCode
            WHERE conn.itemCode = ?
            """,
            [item_code]
        )
    if not rows:
        return "No cities found."
    return ", ".join(r['name'] for r in rows)