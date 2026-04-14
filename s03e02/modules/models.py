from pydantic import BaseModel, Field


# ── Models ──────────────────────────────────────────────────────────────────

class ShellCommandInput(BaseModel):
    cmd: str = Field(description="Command to execute on the remote VM shell, e.g. 'ls /opt/firmware'")


class SubmitAnswerInput(BaseModel):
    confirmation: str = Field(description="The ECCS-xxx code obtained from running the firmware binary")