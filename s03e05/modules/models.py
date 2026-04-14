from typing import Literal
from pydantic import BaseModel, Field


class SubmitAnswerInput(BaseModel):
    answer: list[str] = Field(
        description="List of moves starting with vehicle name, followed by directions: 'up', 'down', 'left', 'right'."
    )
    
class SearchToolsInput(BaseModel):
    query: str = Field(
        description="Natural language description of what you need, e.g. 'I need notes about movement rules and terrain'."
    )

class QueryToolInput(BaseModel):
    url: str = Field(description="URL of the tool to call, as returned by search_tools.")
    query: str = Field(description="Natural language query to send to the tool.")
