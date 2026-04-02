from typing import Any, Dict, List, Optional
from enum import IntEnum
from pydantic import BaseModel, Field


class WindpowerCode(IntEnum):
    NO_RESULT_YET = 11
    RESULT_RETRIEVED = 12
    HELP = 13
    SESSION_STARTED = 60


class SubmitAnswerInput(BaseModel):
    action: str = Field(
        description="API action name. Call get_help() first to learn valid actions and required fields."
    )
    param: Optional[str] = Field(None, description="Required for action='get'. Valid values returned by get_help().")
    startDate: Optional[str] = Field(None, description="Required for 'config' and 'unlockCodeGenerator'. Format: YYYY-MM-DD.")
    startHour: Optional[str] = Field(None, description="Required for 'config' and 'unlockCodeGenerator'. Format: HH:00:00.")
    pitchAngle: Optional[int] = Field(None, description="Required for 'config' and 'unlockCodeGenerator'. Blade pitch angle in degrees.")
    turbineMode: Optional[str] = Field(None, description="Required for single 'config'. Valid values returned by get_help().")
    unlockCode: Optional[str] = Field(None, description="Required for single 'config'. Value obtained from unlockCodeGenerator.")
    windMs: Optional[float] = Field(None, description="Required for 'unlockCodeGenerator'. Wind speed in m/s.")
    configs: Optional[List[Dict[str, Any]]] = Field(None, description="Required for batch 'config'. Array of config-point objects. Each element must have: startDate (YYYY-MM-DD), startHour (HH:00:00), pitchAngle (int), turbineMode (str), unlockCode (str). Example: [{\"startDate\": \"2026-04-03\", \"startHour\": \"18:00:00\", \"pitchAngle\": 90, \"turbineMode\": \"idle\", \"unlockCode\": \"abc123\"}]")

