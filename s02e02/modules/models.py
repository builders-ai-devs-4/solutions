
from pydantic import BaseModel, Field

class RotateCellInput(BaseModel):
    col: int = Field(..., ge=1, le=3, description="Column 1-3 (left to right)")
    row: int = Field(..., ge=1, le=3, description="Row 1-3 (top to bottom)")

class AnswerModel(BaseModel):
    rotate: str = Field(
        ...,
        description="Cell to rotate in format 'COLxROW', e.g. '2x3'",
        pattern=r"^\d+x\d+$"
    )

class SolutionUrlRequest(BaseModel):
    apikey: str
    task: str
    answer: AnswerModel