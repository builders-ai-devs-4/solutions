from typing import Any, Dict
from enum import IntEnum
from pydantic import BaseModel, Field, model_validator


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

    @model_validator(mode="before")
    @classmethod
    def auto_wrap(cls, values: Any) -> Any:
        """If the LLM sends the action dict directly (without wrapping in 'answer'),
        auto-wrap it so {'action': 'start'} becomes {'answer': {'action': 'start'}}."""
        if isinstance(values, dict) and "answer" not in values and "action" in values:
            return {"answer": values}
        return values

