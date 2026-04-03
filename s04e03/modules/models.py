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
    

class SendActionInput(BaseModel):
    """
    Input schema for the send_action tool.

    This model carries a single Domatowo API action payload, for example:
    {"action": "getMap"} or
    {"action": "create", "type": "transporter", "passengers": 2}.
    """

    action: str = Field(
        description="Domatowo API action name, e.g. 'getMap', 'create', 'move', 'inspect'."
    )
    # optional, action-specific fields:
    type: str | None = Field(
        default=None,
        description="Action-specific type, e.g. 'transporter' or 'scout' for 'create'."
    )
    passengers: int | None = Field(
        default=None,
        description="Number of passengers for transporter creation or dismount (1-4)."
    )
    object: str | None = Field(
        default=None,
        description="Object identifier (hash) for actions like 'move', 'inspect', 'dismount'."
    )
    where: str | None = Field(
        default=None,
        description="Destination field (A1..K11) for 'move'."
    )
    symbol: str | None = Field(
        default=None,
        description="2-character symbol for 'searchSymbol'."
    )
    destination: str | None = Field(
        default=None,
        description="Destination field (A1..K11) for 'callHelicopter'."
    )
    symbols: list[str] | None = Field(
        default=None,
        description=(
            "Optional list of symbols/coordinates for 'getMap', "
            "e.g. ['KS', 'SZ', 'B3', 'C4']."
        )
    )

    
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