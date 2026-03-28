from pathlib import Path
import re
import sys
from typing import Optional
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
import os
from langchain_openrouter import ChatOpenRouter
import requests
from modules.models import SensorReading, SensorValidationResult
from pydantic import BaseModel, Field

from database import SensorDatabase, run_validation, run_validation

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from libs.loggers import agent_logger
import json

DATA_FOLDER_PATH    = os.environ["DATA_FOLDER_PATH"]
PARENT_FOLDER_PATH  = os.environ["PARENT_FOLDER_PATH"]
TASK_DATA_FOLDER_PATH = os.environ["TASK_DATA_FOLDER_PATH"]

DB_PATH = os.environ["DB_PATH"]

FLAG_RE = re.compile(r"\{FLG:[^}]+\}")
MAX_TOOL_ITERATIONS = 10 
_RECURSION_LIMIT = MAX_TOOL_ITERATIONS * 10 + 2  # 102
CHUNK_SIZE = int(os.environ["CHUNK_SIZE"])
from cache import cache

@tool(response_format="content_and_artifact")
def run_sensor_validation(db_path: str) -> tuple[str, list[SensorValidationResult]]:
    """
    Load sensor readings from the database and validate them in a single step.

    Validates each reading for range violations and inactive sensor anomalies.
    Processes readings in chunks from memory after a single database read.

    Args:
        db_path: Path to the DuckDB database file as a string.

    Returns:
        Content: JSON string with anomaly details readable by the agent.
        Artifact: list[SensorValidationResult] — one result per anomalous record.
    """

    with SensorDatabase(Path(db_path)) as db:
        readings = db.load_readings()

    if not readings:
        return "No records found in the database.", []

    anomalies: list[SensorValidationResult] = []

    agent_logger.info(f"[run_sensor_validation] chunk_size={CHUNK_SIZE}")
    
    for i in range(0, len(readings), CHUNK_SIZE):
        chunk   = readings[i : i + CHUNK_SIZE]
        results = run_validation(chunk)
        anomalies.extend(r for r in results if r.is_anomaly)
        agent_logger.info(f"[run_sensor_validation] processed chunk {i // CHUNK_SIZE + 1}/{(len(readings) + CHUNK_SIZE - 1) // CHUNK_SIZE}")
    cache.store_validation(anomalies)
    
    agent_logger.info(f"[run_sensor_validation] anomalies={len(anomalies)})")
    
    content = json.dumps(
        [
            {
                "filename":       r.filename,
                "sensor_type":    r.reading.sensor_type,
                "timestamp":      r.reading.timestamp,
                "range_errors":   r.range_errors,
                "inactive_errors":r.inactive_errors,
            }
            for r in anomalies
        ],
        ensure_ascii=False,
        indent=2,
    )
    return content, anomalies

@tool(response_format="content_and_artifact")
def analyze_operator_notes(db_path: str) -> tuple[str, list[SensorValidationResult]]:
    """
    Analyze operator notes for semantic anomalies using LLM.

    Detects:
    - Operator claims OK but sensor data failed validation (missed real problem).
    - Operator reports errors but data is within normal range (false alarm).

    Deduplicates identical notes before sending to LLM — technicians often
    reuse the same notes across many files, so only unique notes are analyzed.
    Results are mapped back to all files sharing the same note.

    Processes unique notes in chunks to respect LLM context window limits.
    Minimizes LLM output — model returns only flagged note text and reason.

    Args:
        db_path: Path to the DuckDB database file as a string.

    Returns:
        Content: JSON string of flagged readings with anomaly reasons.
        Artifact: list[SensorValidationResult] with operator_errors populated.
    """
    with SensorDatabase(Path(db_path)) as db:
        readings = db.load_readings()

    if not readings:
        return "No records found in the database.", []

    # Files that already failed sensor validation
    validated_error_files: set[str] = {
        r.filename
        for r in cache.get_validation_results()
        if r.sensor_errors  # only truly failed ones
    }

    # Deduplication: note → list of files that use it
    note_to_files: dict[str, list[SensorReading]] = {}
    for r in readings:
        note_to_files.setdefault(r.operator_notes, []).append(r)

    # Build enriched unique-note list with data-error context
    unique_notes_with_context = [
        {
            "note": note,
            "has_data_error": any(
                r.filename in validated_error_files
                for r in file_readings
            ),
        }
        for note, file_readings in note_to_files.items()
    ]

    agent_logger.info(
        f"[analyze_operator_notes] {len(readings)} readings → "
        f"{len(unique_notes_with_context)} unique notes to analyze"
    )

    llm = ChatOpenRouter(model="google/gemini-3-flash-preview", temperature=0)
    notes_prompt = (Path(PARENT_FOLDER_PATH) / "prompts" / "notes_analysis.md").read_text(encoding="utf-8")
    chain = ChatPromptTemplate.from_messages([
        ("system", notes_prompt),
        ("human", "{notes}"),
    ]) | llm

    anomalies: list[SensorValidationResult] = []

    # Process chunks of unique notes — not files — to minimize LLM calls
    for i in range(0, len(unique_notes_with_context), CHUNK_SIZE):
        chunk = unique_notes_with_context[i : i + CHUNK_SIZE]
        payload = json.dumps(chunk, ensure_ascii=False, indent=2)

        try:
            response = chain.invoke({"notes": payload})
            flagged  = json.loads(response.content)
        except json.JSONDecodeError:
            agent_logger.warning(
                f"[analyze_operator_notes] Invalid JSON from LLM, chunk {i}, skipping."
            )
            flagged = []

        # Map flagged notes back to all files that use them
        for item in flagged:
            flagged_note = item["note"]
            reason       = item["reason"]

            for reading in note_to_files.get(flagged_note, []):
                anomalies.append(SensorValidationResult(
                    reading         = reading,
                    operator_errors = [reason],
                ))

    cache.store_notes(anomalies)

    if not anomalies:
        return "No suspicious operator notes detected.", []

    content = json.dumps(
        [
            {
                "filename":        r.filename,
                "sensor_type":     r.reading.sensor_type,
                "operator_errors": r.operator_errors,
            }
            for r in anomalies
        ],
        ensure_ascii=False,
        indent=2,
    )
    return content, anomalies

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


class SendAnomaliesInput(BaseModel):
    filenames: list[str] = Field(
        description="List of anomalous filenames to report, e.g. ['0158.json', '0307.json']"
    )


@tool(args_schema=SendAnomaliesInput, response_format="content_and_artifact")
def send_anomalies_to_central(filenames: list[str]) -> tuple[str, dict]:
    """
    Send anomalous file identifiers to the central verification endpoint.

    Call this after both run_sensor_validation and analyze_operator_notes are complete.
    Pass the combined list of anomalous filenames from both tools.

    Args:
        filenames: List of anomalous filenames, e.g. ['0158.json', '0307.json'].

    Returns:
        Content: Central server response with verification result.
        Artifact: Full request payload sent to central.
    """
    apikey       = os.environ["AIDEVS_SECRET"]
    solution_url = os.environ["SOLUTION_URL"]
    task_name    = os.environ["TASK_NAME"]

    # Deduplicate i posortuj
    anomaly_files = sorted(set(filenames))

    agent_logger.info(f"[send_anomalies_to_central] anomaly_files={len(anomaly_files)})")

    payload = {
        "apikey": apikey,
        "task":   task_name,
        "answer": {"recheck": anomaly_files},
    }
    agent_logger.info(f"[send_anomalies_to_central] recheck={anomaly_files}")

    response = requests.post(solution_url, json=payload)

    if not response.ok:
        return (
            f"Server rejected the request with {response.status_code}: {response.text}. "
            f"Sent {len(anomaly_files)} files. Review the list and retry.",
            payload,
        )
    agent_logger.info(f"[send_anomalies_to_central] response_status={response.status_code}")

    result  = response.json()
    content = json.dumps(result, ensure_ascii=False, indent=2)
    return content, payload