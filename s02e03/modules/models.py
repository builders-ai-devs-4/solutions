
from pydantic import BaseModel, Field

class AnswerModel(BaseModel):
    logs: str = Field(..., description="Logs or explanation of the failure, extracted from the failure log.")

class SolutionUrlRequest(BaseModel):
    apikey: str
    task: str
    answer: AnswerModel