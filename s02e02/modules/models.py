
from pydantic import BaseModel, Field

class RotateCellInput(BaseModel):
    col: int = Field(..., ge=0, le=2, description="Column index, becomes first part of 'COLxROW'")
    row: int = Field(..., ge=0, le=2, description="Row index, becomes second part of 'COLxROW'")

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