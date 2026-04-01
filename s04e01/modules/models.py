from typing import Literal
from pydantic import BaseModel, Field


class SubmitAnswerInput(BaseModel):
    action: dict = Field(
        description=(
            "Full answer payload as a dict. "
            "Known actions: {'action': 'help'} to get API docs, {'action': 'done'} to finalize. "
            "For other actions: discover required fields first by calling with {'action': 'help'}."
        )
    )
    
class FetchOkoPageInput(BaseModel):
    path: str = Field(
        description=(
            "Relative path on the OKO panel, e.g. '/', '/reports', '/tasks/abc123'. "
            "Start with '/' to discover navigation. Follow links found in the content."
        )
    )