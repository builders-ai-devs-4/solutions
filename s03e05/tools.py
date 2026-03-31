import os
import sys
import time
from typing import Optional
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import requests


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

AI_DEVS_SECRET     = os.environ["AI_DEVS_SECRET"]
TASK_NAME          = os.environ["TASK_NAME"]
SOLUTION_URL       = os.environ["SOLUTION_URL"]
PARENT_FOLDER_PATH = os.environ["PARENT_FOLDER_PATH"]
DATA_FOLDER_PATH   = os.environ["DATA_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]
TOOLSEARCH_URL     = os.getenv('TOOLSEARCH_URL')

MAX_TOOL_ITERATIONS = 20
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 10 + 2  # 202

from libs.loggers import agent_logger
from libs.central_client import _post_to_central, _scan_flag_in_response
from modules.models import QueryToolInput, SearchToolsInput, SubmitAnswerInput

@tool(args_schema=SubmitAnswerInput, response_format="content_and_artifact")
def submit_answer(answer: list[str]) -> tuple[str, dict]:
    """
    Submit the final answer to the central verification endpoint.
    Call this only when you have the complete and confirmed answer ready.
    After calling this tool, ALWAYS call scan_flag on the response.
    """
    return _post_to_central({"answer": answer})

@tool
def scan_flag(text: str) -> Optional[str]:
    """
    Search for a success flag matching the pattern {FLG:...} in the given text.
    Call this tool to analyze the server's response after submitting a solution to verify task completion.
    """
    flag = _scan_flag_in_response(text)
    if flag:
        agent_logger.info(f"[scan_flag] Flag found: {flag}")
        return flag
    agent_logger.info(f"[scan_flag] no flag in text={text}")
    return None

@tool(args_schema=SearchToolsInput)
def search_tools(query: str) -> str:
    """
    Search for available tools by describing what you need in natural language.
    Use this to discover tools before solving the task.
    Returns a list of available tools matching the query.
    """
    agent_logger.info(f"[search_tools] query={query}")
    
    response = requests.post(
        TOOLSEARCH_URL,
        json={
            "apikey": AI_DEVS_SECRET,
            "query": query,
        }
    )
    agent_logger.info(f"[search_tools] response.text={response.text}")
    
    return response.text

@tool(args_schema=QueryToolInput)
def query_tool(url: str, query: str) -> str:
    """
    Call a discovered tool by its URL with a natural language query.
    Use this after search_tools returns a tool URL to actually fetch data from it.
    """
    agent_logger.info(f"[query_tool] query={query}")
    
    response = requests.post(
        url,
        json={
            "apikey": AI_DEVS_SECRET,
            "query": query,
        }
    )
    agent_logger.info(f"[query_tool] response.text={response.text}")
   
    return response.text