from typing import Any, Dict, List, Optional, TypedDict
from enum import IntEnum
from pydantic import BaseModel, Field, model_validator

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

    This model is used for simple central actions that consist of:
    - a required action name,
    - an optional destination field.

    It is suitable for actions such as:
    - "done"
    - "help"
    - "callHelicopter" (requires destination)
    """

    action: str = Field(
        description=(
            "Central action name, for example 'done', 'help', or 'callHelicopter'."
        )
    )
    destination: str | None = Field(
        default=None,
        description=(
            "Optional destination coordinate, e.g. 'F6'. "
            "Required when action is 'callHelicopter'."
        )
    )

    @model_validator(mode="after")
    def validate_action_payload(self) -> "SubmitAnswerInput":
        """
        Validate action-specific payload constraints.

        Rules:
        - 'callHelicopter' requires destination
        - other actions should not include destination
        """
        if self.action == "callHelicopter" and not self.destination:
            raise ValueError("destination is required when action='callHelicopter'")

        if self.action != "callHelicopter" and self.destination is not None:
            raise ValueError(
                "destination should only be provided when action='callHelicopter'"
            )

        return self
    
class AnalyzeMapInput(BaseModel):
    """
    Input schema for the analyze_map tool.

    This model carries the raw map payload returned by the getMap action.
    The payload may be either:
    - the full API response containing a nested "map" object, or
    - the "map" object itself.

    The value is expected to be a JSON string because tool inputs are
    passed through the agent/tool interface as serialized text.
    """

    raw_map: str = Field(
        description=(
            "Raw map payload as a JSON string. "
            "It may contain either the full getMap response or only the nested map object."
        )
    )