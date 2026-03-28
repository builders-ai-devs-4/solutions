import os
import re
import sys
import time
from typing import Optional
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import requests

from modules.models import ShellCommandInput, SubmitAnswerInput

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.loggers import agent_logger

AI_DEVS_SECRET = os.environ["AI_DEVS_SECRET"]
SOLUTION_URL   = os.environ["SOLUTION_URL"]
SHELL_URL      = os.environ["SHELL_URL"]
TASK_NAME      = os.environ["TASK_NAME"]

FLAG_RE = re.compile(r"\{FLG:[^}]+\}")
ECCS_RE = re.compile(r"ECCS-[A-Za-z0-9]{40,}")
MAX_TOOL_ITERATIONS = 20
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 10 + 2  # 202


# ── Tools ───────────────────────────────────────────────────────────────────

@tool(args_schema=ShellCommandInput)
def shell_command(cmd: str) -> str:
    """
    Execute a shell command on the remote virtual machine via HTTP API.
    Use 'help' first to discover available commands — this is a non-standard shell.
    Returns the command output or an error description.
    """
    payload = {"apikey": AI_DEVS_SECRET, "cmd": cmd}
    agent_logger.info(f"[shell_command] cmd={cmd!r}")

    for attempt in range(3):
        try:
            response = requests.post(SHELL_URL, json=payload, timeout=30)

            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 5))
                agent_logger.warning(f"[shell_command] RATE_LIMIT — waiting {wait}s")
                time.sleep(wait)
                continue

            if response.status_code == 403:
                data = response.json()
                ban_time = data.get("wait", "?")
                agent_logger.error(f"[shell_command] BAN for {ban_time}s — security violation")
                return f"BAN: Security violation. Access blocked for {ban_time} seconds. Wait before retrying."

            if response.status_code == 503:
                agent_logger.warning(f"[shell_command] 503 — waiting 3s")
                time.sleep(3)
                continue

            result = response.json().get("output", response.text)
            agent_logger.info(f"[shell_command] output={str(result)[:200]}")
            return result

        except requests.RequestException as e:
            agent_logger.error(f"[shell_command] attempt={attempt} error={e}")
            time.sleep(2)

    return "ERROR: Failed to reach shell API after 3 attempts."


@tool(args_schema=SubmitAnswerInput, response_format="content_and_artifact")
def submit_answer(confirmation: str) -> tuple[str, dict]:
    """
    Submit the obtained ECCS-xxx code to the central verification endpoint.
    Call this only after you have confirmed the code by running the firmware binary.
    """
    payload = {
        "apikey": AI_DEVS_SECRET,
        "task": TASK_NAME,
        "answer": {"confirmation": confirmation},
    }
    agent_logger.info(f"[submit_answer] confirmation={confirmation}")
    response = requests.post(SOLUTION_URL, json=payload)

    if not response.ok:
        return (
            f"Server rejected with {response.status_code}: {response.text}",
            payload,
        )

    result  = response.json()
    content = str(result)
    agent_logger.info(f"[submit_answer] response={content}")
    return content, payload

@tool
def scan_flag(text: str) -> Optional[str]:
    """
    Search for a success flag matching the pattern {FLG:...} in the given text.
    Call this tool to analyze the server's response after submitting a solution to verify task completion.
    """
    match = FLAG_RE.search(text)
    if match:
        agent_logger.info(f"[FLAG FOUND] {match.group(0)}")
        return match.group(0)
    agent_logger.info(f"[scan_flag] no flag in text (len={len(text)})")
    return None

@tool
def scan_eccs_flag(text: str) -> Optional[str]:
    """
    Search for a success code matching the pattern ECCS-xxx in the given text.
    Call this after running the binary to extract the code from its output.
    """
    match = ECCS_RE.search(text)
    if match:
        agent_logger.info(f"[ECCS FOUND] {match.group(0)}")
        return match.group(0)
    agent_logger.info(f"[scan_eccs_flag] no ECCS code in text (len={len(text)})")
    return None

