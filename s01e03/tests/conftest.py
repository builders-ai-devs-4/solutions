import sys
import os
import requests
import pytest
from pathlib import Path
from dotenv import load_dotenv

_project_root = Path(__file__).parent.parent
_solutions    = _project_root.parent

sys.path.insert(0, str(_solutions))           # solutions/ → libs.*
sys.path.insert(0, str(_project_root / "src")) # src/ → models.*, task.*
    
# Read development env if APP_ENV is not set
APP_ENV = os.getenv("APP_ENV", "development")
load_dotenv(_project_root / f".env.{APP_ENV}", override=False)
load_dotenv(Path(__file__).parent.parent / ".env")


# DATA_FOLDER_PATH must be set before log-related imports,
# because loggers use it to determine log file location
_data_folder = _project_root / os.getenv("DATA_FOLDER")
os.environ.setdefault("DATA_FOLDER_PATH",   str(_data_folder))
os.environ.setdefault("PARENT_FOLDER_PATH", str(_project_root))

from libs.logger import get_logger

_log_dir = _data_folder / "logs"
_log = get_logger("e2e", log_dir=_log_dir, log_stem="e2e_tests")

BASE_URL = "http://{}:{}".format(
    os.getenv("APP_HOST", "localhost"),
    os.getenv("APP_PORT", "8000"),
)


@pytest.fixture(scope="session")
def logger():
    """Fixture: logger available in every test."""
    return _log  # było: log


@pytest.fixture(scope="session")
def chat():
    """Fixture: helper for POST requests."""
    def _post(session_id: str, msg: str) -> dict:
        _log.debug(f"[{session_id}] → {msg!r}")  # było: log
        r = requests.post(
            BASE_URL,
            json={"sessionID": session_id, "msg": msg},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        _log.debug(f"[{session_id}] ← {data['msg']!r}")  # było: log
        return data
    return _post