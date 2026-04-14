from typing import Literal

from pydantic import BaseModel, Field

class SubmitAnswerInput(BaseModel):
    command: Literal["start", "right", "left", "wait", "reset"] = Field(
        description="Command to send to the reactor robot: start (initialize), right (move forward), left (move back), wait (skip turn, blocks move), reset (restart)."
    )
