from typing import Literal

from pydantic import BaseModel, Field

class ToolEntry(BaseModel):
    URL: str = Field(
        description="URL endpoint of the tool to be called."
    )
    description: str = Field(
        description="Description of what the tool does and what parameters it accepts in the 'params' field."
    )   

class SubmitAnswerInputTools(BaseModel):
    tools: list[ToolEntry] = Field(
        description="List of tools to register. Each tool needs a URL endpoint and a description of its functionality and accepted params."
    )


class SubmitAnswerInputCheck(BaseModel):
    action: Literal["check"] = Field(
        default="check",
        description="Action to perform. Use 'check' to verify the current negotiations status."
    )