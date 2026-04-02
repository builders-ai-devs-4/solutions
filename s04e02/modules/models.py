from typing import Any, Dict
from enum import IntEnum
from pydantic import BaseModel, Field


class WindpowerCode(IntEnum):
    NO_RESULT_YET = 11
    RESULT_RETRIEVED = 12
    HELP = 13
    SESSION_STARTED = 60


class SubmitAnswerInput(BaseModel):
    answer: Dict[str, Any] = Field(
        description=(
            "Full answer payload. Must include 'action' key plus any required fields. "
            "Known actions: 'start', 'config' (single or batch via 'configs'), 'done'. "
            "Additional actions available after calling get_help()."
        )
    )
    
