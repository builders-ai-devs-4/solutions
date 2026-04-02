from typing import Any, Dict
from enum import IntEnum
from pydantic import BaseModel, ConfigDict, Field


class WindpowerCode(IntEnum):
    NO_RESULT_YET = 11
    RESULT_RETRIEVED = 12
    HELP = 13
    SESSION_STARTED = 60


class SubmitAnswerInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    action: str = Field(
        description=(
            "API action name. Call get_help() first to learn all available actions "
            "and their required parameters. Pass all additional required fields "
            "(e.g. param, startDate, startHour, windMs, pitchAngle, configs) "
            "alongside action based on what get_help() returns."
        )
    )

