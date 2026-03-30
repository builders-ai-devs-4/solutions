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
from libs.loggers import agent_logger

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

@tool
def search_items(keyword: str) -> str:
    """Search items in the database by keyword.
    Returns matching item names and their codes.
    Use this first to find the item code before looking up cities."""
    with Database.connect(DB_PATH, read_only=True) as conn:
        rows = conn.execute("""
            SELECT name, code FROM items
            WHERE name ILIKE ? LIMIT 20
        """, [f"%{keyword}%"]).fetchall()
    if not rows:
        return "No items found."
    return "\n".join(f"{name} ({code})" for name, code in rows)


@tool
def get_cities_for_item(item_code: str) -> str:
    """Get all city names that have a specific item available, by item code.
    Returns a comma-separated list of city names."""
    with Database.connect(DB_PATH, read_only=True) as conn:
        rows = conn.execute("""
            SELECT DISTINCT c.name FROM cities c
            JOIN connections conn ON c.code = conn.cityCode
            WHERE conn.itemCode = ?
        """, [item_code]).fetchall()
    if not rows:
        return "No cities found."
    return ", ".join(row[0] for row in rows)