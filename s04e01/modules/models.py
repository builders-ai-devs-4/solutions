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

class OkoUpdateInput(BaseModel):
    page: Literal["incydenty", "notatki", "zadania"] = Field(
        description="Target page to update."
    )
    id: str = Field(
        min_length=32,
        max_length=32,
        description="32-char hex id of the record to update.",
    )
    title: str | None = Field(
        default=None,
        description="New title (optional, at least one of title/content/done must be provided).",
    )
    content: str | None = Field(
        default=None,
        description="New content/description text (optional).",
    )
    done: Literal["YES", "NO"] | None = Field(
        default=None,
        description='Completion flag, allowed only for page "zadania".',
    )
