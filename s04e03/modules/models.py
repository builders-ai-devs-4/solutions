from typing import Any, Dict, List, Optional, TypedDict
from enum import IntEnum
from pydantic import BaseModel, Field


class SupervisorState(TypedDict):
    total_budget: int        # 300
    used_per_explorer: dict  # {"explorer_0": 45, "explorer_1": 38}
    found_at: str | None     # koordynaty gdy cel znaleziony
    clusters: list[dict]



class CallHelicopterInput(BaseModel):
    """
    Input schema for the call_helicopter tool.

    Attributes:
        destination: Grid coordinates of the field where a scout confirmed
                     the target's presence. The helicopter will land here.
                     Format: column letter + row number, e.g. 'F6'.
    """

    destination: str
    

class SubmitAnswerInput(BaseModel):
    """
    Input schema for the submit_answer tool.

    Attributes:
        action: Action name to send to the central API, e.g. 'done', 'getMap', 'callHelicopter'.
        destination: Optional grid coordinates required only for the 'callHelicopter' action,
                     e.g. 'F6'. Ignored for all other actions.
    """

    action: str
    destination: str | None = None
    
