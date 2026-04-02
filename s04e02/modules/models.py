from typing import Any, Dict
from pydantic import BaseModel, Field


class SubmitAnswerInput(BaseModel):
    answer: Dict[str, Any] = Field(
        description=(
            "Full answer payload. Must include 'action' key plus any required fields. "
            "Known actions: 'start', 'config' (single or batch via 'configs'), 'done'. "
            "Additional actions available after calling get_help()."
        )
    )
    
