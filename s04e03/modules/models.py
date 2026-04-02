from typing import Any, Dict, List, Optional, TypedDict
from enum import IntEnum
from pydantic import BaseModel, Field


class SupervisorState(TypedDict):
    total_budget: int        # 300
    used_per_explorer: dict  # {"explorer_0": 45, "explorer_1": 38}
    found_at: str | None     # koordynaty gdy cel znaleziony
    clusters: list[dict]