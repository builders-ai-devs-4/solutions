import sys
import os
import requests
import pytest
from pathlib import Path
from dotenv import load_dotenv

_src  = Path(__file__).parent.parent / "src"
_solutions = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_solutions))  # solutions/ → libs.*
sys.path.insert(0, str(_src))        # src/ → models.*, task.*

load_dotenv(Path(__file__).parent.parent / ".env")

# DATA_FOLDER_PATHmust be ste befor log related imports, because loggers use it to determine log file location
from dotenv import dotenv_values
_env = dotenv_values(Path(__file__).parent.parent / ".env")
_data_folder = Path(__file__).parent.parent / _env.get("DATA_FOLDER", ".data")
os.environ.setdefault("DATA_FOLDER_PATH", str(_data_folder))
os.environ.setdefault("PARENT_FOLDER_PATH", str(Path(__file__).parent.parent))

from libs.logger import get_logger

_log_dir = Path(os.environ["DATA_FOLDER_PATH"]) / "logs"
log = get_logger("e2e", log_dir=_log_dir, log_stem="e2e_tests")

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="session")
def logger():
    """Fixture: logger available on every test"""
    return log

@pytest.fixture(scope="session")
def chat():
    """Fixture: helper for POST requests"""
    def _post(session_id: str, msg: str) -> dict:
        log.debug(f"[{session_id}] → {msg!r}")
        r = requests.post(
            BASE_URL,
            json={"sessionID": session_id, "msg": msg},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        log.debug(f"[{session_id}] ← {data['msg']!r}")
        return data
    return _post