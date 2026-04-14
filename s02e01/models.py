from pydantic import BaseModel
from typing import Optional, Literal

class ItemResponse(BaseModel):
    id: str
    description: str
    server_code: int
    server_message: str

class ExecutorResult(BaseModel):
    status: Literal["completed", "flag_found", "error"]
    flag: Optional[str] = None
    responses: list[ItemResponse] = []
    errors: list[ItemResponse] = []
