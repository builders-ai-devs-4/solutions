
from pydantic import BaseModel, Field

class AnswerModel(BaseModel):
    prompt: str

class SolutionUrlRequest(BaseModel):
    apikey: str
    task: str
    answer: AnswerModel