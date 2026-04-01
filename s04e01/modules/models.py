from typing import Literal
from pydantic import BaseModel, Field


class SubmitAnswerInput(BaseModel):
    action: str = Field(
        description="Action name (e.g. 'help', 'done'). For more complex actions, supervisor will provide full answer payload another way."
    )
    
class FetchOkoPageInput(BaseModel):
    path: str = Field(
        description=(
            "Relative path on the OKO panel, e.g. '/', '/reports', '/tasks/abc123'. "
            "Start with '/' to discover navigation. Follow links found in the content."
        )
    )
