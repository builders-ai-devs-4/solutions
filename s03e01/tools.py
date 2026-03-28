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
from modules.models import SensorReading, ValidationResult
from dotenv import load_dotenv

from s03e01.database import SensorDatabase, run_validation, run_validation

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from libs.filetype_detect import detect_file_type
from libs.generic_helpers import get_filename_from_url, read_file_text, save_file, save_json_file
from libs.loggers import agent_logger
import json

DB_PATH = os.environ["DB_PATH"]


@tool(response_format="content_and_artifact")
def run_sensor_validation(DB_PATH) -> tuple[str, list[str]]:
    """
    Validate all sensor readings loaded by load_sensor_readings.

    Checks each reading for:
    - Active sensor values outside their valid operational range.
    - Inactive sensors reporting non-zero measurement values.

    Must be called after load_sensor_readings.

    Returns:
        Validation summary with anomaly count and list of affected file names.
        Artifact: sorted list of file names containing at least one anomaly.
    """
    
    with SensorDatabase(DB_PATH) as db:
        _readings = db.load_readings()

    if not _readings:
        return "No readings loaded. Call load_sensor_readings first.", []

    _results = run_validation(_readings)

    anomalies     = [r for r in _results if r.is_anomaly]
    anomaly_files = sorted({r.filename for r in anomalies})

    content = (
        f"Validation complete. {len(_results)} records checked, "
        f"{len(anomalies)} anomalies found in {len(anomaly_files)} files:\n" +
        "\n".join(f"  - {f}" for f in anomaly_files)
    )
    return content, anomaly_files