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
MAX_OUTPUT_CHARS   = 8_000
MAX_RETRIES        = 3
RATE_LIMIT_BACKOFF = [10, 30, 60]

_BINARY_READ_RE = re.compile(
    r'\bcat\b.*\.(bin|exe|so|o|elf|img|dat|out)\b'
    r'|\bxxd\b|\bod\b|\bhexdump\b',
    re.IGNORECASE
)


def _is_binary_output(text: str) -> bool:
    """Return True if output contains significant amount of non-printable characters."""
    if not text:
        return False
    non_printable = sum(1 for c in text if ord(c) < 32 and c not in '\n\r\t')
    return non_printable / len(text) > 0.1


@tool(args_schema=ShellCommandInput)
def shell_command(cmd: str) -> str:
    """
    Execute a shell command on the remote virtual machine via HTTP API.
    Use 'help' first to discover available commands — this is a non-standard shell.
    NEVER cat binary files (.bin, .exe, .so) — use 'strings <file>' instead.
    Returns the command output or an error description.
    """
    if _BINARY_READ_RE.search(cmd):
        agent_logger.warning(f"[shell_command] BLOCKED binary read: {cmd!r}")
        return (
            f"[BLOCKED] Command '{cmd}' would read a binary file directly. "
            f"Use 'strings {cmd.split()[-1]}' to extract readable text instead."
        )

    payload = {"apikey": AI_DEVS_SECRET, "cmd": cmd}
    agent_logger.info(f"[shell_command] cmd={cmd!r}")

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(SHELL_URL, json=payload, timeout=30)
            agent_logger.info(f"[shell_command] HTTP {response.status_code} (attempt {attempt + 1}/{MAX_RETRIES})")

            if response.status_code == 429:
                wait = max(
                    int(response.headers.get("Retry-After", 0)),
                    RATE_LIMIT_BACKOFF[attempt],
                )
                agent_logger.warning(f"[shell_command] RATE_LIMIT — waiting {wait}s")
                time.sleep(wait)
                continue

            if response.status_code == 403:
                data = response.json()
                ban_time = data.get("wait", "?")
                agent_logger.error(f"[shell_command] BAN for {ban_time}s — security violation")
                return f"BAN: Security violation. Access blocked for {ban_time} seconds. Wait before retrying."

            if response.status_code == 503:
                agent_logger.warning(f"[shell_command] 503 Service Unavailable — waiting 3s")
                time.sleep(3)
                continue

            if not response.ok:
                agent_logger.error(f"[shell_command] Unexpected HTTP {response.status_code}: {response.text[:200]}")
                return f"ERROR: Unexpected server response {response.status_code}: {response.text[:200]}"

            result = str(response.json().get("output", response.text))

            if _is_binary_output(result):
                agent_logger.warning(f"[shell_command] binary output detected for cmd={cmd!r}")
                return (
                    f"[BINARY OUTPUT DETECTED] Command '{cmd}' returned binary data. "
                    f"Use 'strings <file>' to extract readable text instead."
                )

            if len(result) > MAX_OUTPUT_CHARS:
                agent_logger.warning(f"[shell_command] output truncated {len(result)} -> {MAX_OUTPUT_CHARS}")
                result = result[:MAX_OUTPUT_CHARS] + f"\n\n[TRUNCATED — {len(result)} chars total]"

            agent_logger.info(f"[shell_command] output={result[:200]}")
            return result

        except requests.RequestException as e:
            agent_logger.error(f"[shell_command] attempt={attempt + 1}/{MAX_RETRIES} network error: {e}")
            time.sleep(2)

    agent_logger.error("[shell_command] all retries exhausted — rate limit persists")
    return (
        "RATE_LIMITED: Shell API is still rate limited after all retry attempts. "
        "Do NOT call any shell commands for the next 2 minutes. "
        "Review what you already know and plan your next steps."
    )
    
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

