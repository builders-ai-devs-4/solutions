from pathlib import Path
import re
import sys
from typing import Optional
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
import os
from langchain_openrouter import ChatOpenRouter
from langchain.messages import SystemMessage, HumanMessage
import requests
from datetime import datetime, date
from modules.models import SensorReading, SensorValidationResult, ValidationResult
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from database import SensorDatabase, run_validation, run_validation

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from libs.filetype_detect import detect_file_type
from libs.generic_helpers import get_filename_from_url, read_file_text, save_file, save_json_file
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
    Analyze operator notes for all sensor readings using LLM.

    Detects anomalies that cannot be caught by range validation, including:
    - Notes contradicting the measured values or sensor type.
    - Suspicious, uncertain, or copy-pasted operator observations.
    - Semantic inconsistencies between note content and sensor context.

    Processes readings in chunks to respect LLM context window limits.
    Maps LLM results back to SensorValidationResult using filename + timestamp.

    Args:
        db_path: Path to the DuckDB database file as a string.

    Returns:
        Content: JSON string of flagged readings with anomaly reasons.
        Artifact: list[SensorValidationResult] with operator_errors populated,
                  one result per flagged reading.
    """

    agent_logger.info(f"[analyze_operator_notes] chunk_size={CHUNK_SIZE}")
    
    with SensorDatabase(Path(db_path)) as db:
        readings = db.load_readings()

    if not readings:
        return "No records found in the database.", []

    # Indeks do szybkiego wyszukiwania SensorReading po (filename, timestamp)
    readings_index: dict[tuple[str, int], SensorReading] = {
        (Path(r.filename).name, r.timestamp): r
        for r in readings
    }

    NOTES_ANALYSIS_PROMPT = (Path(PARENT_FOLDER_PATH) / "prompts" / "seeker_user.md").read_text(encoding="utf-8")
    
    
    llm   = ChatOpenRouter(model="openai/gpt-5-mini", temperature=0)
    chain = NOTES_ANALYSIS_PROMPT | llm

    anomalies: list[SensorValidationResult] = []

    for i in range(0, len(readings), CHUNK_SIZE):
        chunk = readings[i : i + CHUNK_SIZE]

        payload = json.dumps(
            [
                {
                    "filename":       Path(r.filename).name,
                    "timestamp":      r.timestamp,
                    "sensor_type":    r.sensor_type,
                    "operator_notes": r.operator_notes,
                }
                for r in chunk
            ],
            ensure_ascii=False,
            indent=2,
        )

        response = chain.invoke({"readings": payload})

        try:
            flagged = json.loads(response.content)
        except json.JSONDecodeError:
            agent_logger.warning(f"[analyze_operator_notes] Invalid JSON from LLM for chunk {i}, skipping.")
            flagged = []
            continue
        flagged  = json.loads(response.content)

        for item in flagged:                        # ← wewnątrz tej samej pętli
            key     = (item["filename"], item["timestamp"])
            reading = readings_index.get(key)
            if reading:
                anomalies.append(SensorValidationResult(
                    reading         = reading,
                    operator_errors = [item["reason"]],
                ))

    cache.store_notes(anomalies)
    
    if not anomalies:
        return "No suspicious operator notes detected.", []
    
    agent_logger.info(f"[analyze_operator_notes] anomalies={len(anomalies)})")

    content = json.dumps(
        [
            {
                "filename":       r.filename,
                "sensor_type":    r.reading.sensor_type,
                "timestamp":      r.reading.timestamp,
                "operator_errors":r.operator_errors,
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
    anomalies: list[SensorValidationResult] = Field(
        description="List of SensorValidationResult instances from run_sensor_validation "
                    "or analyze_operator_notes. File names are extracted automatically."
    )


@tool(args_schema=SendAnomaliesInput, response_format="content_and_artifact")
def send_anomalies_to_central(anomalies: list[SensorValidationResult]) -> tuple[str, dict]:
    """
    Send anomalous file identifiers to the central verification endpoint.

    Extracts file names from SensorValidationResult instances and submits
    them to the /verify endpoint. Accepts results from both
    run_sensor_validation and analyze_operator_notes.

    File names are sent as-is (e.g. "0001.json") which is an accepted
    format by the central verification endpoint.

    Args:
        anomalies: Validation results produced by run_sensor_validation
                   or analyze_operator_notes.

    Returns:
        Content: Central server response with verification result.
        Artifact: Full request payload sent to central.
    """
    api_key      = os.environ["AI_DEVS_SECRET"]
    solution_url = os.environ["SOLUTION_URL"]
    task_name    = os.environ["TASK_NAME"]

    anomaly_files = sorted({r.filename for r in anomalies})
    agent_logger.info(f"[send_anomalies_to_central] anomaly_files={len(anomaly_files)})")

    payload = {
        "apikey": api_key,
        "task":   task_name,
        "answer": {
            "recheck": anomaly_files
        },
    }

    response = requests.post(solution_url, json=payload)
    response.raise_for_status()
    agent_logger.info(f"[send_anomalies_to_central] response_status={response.status_code}")

    result  = response.json()
    content = json.dumps(result, ensure_ascii=False, indent=2)

    return content, payload