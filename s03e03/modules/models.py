from pydantic import BaseModel, Field

class SubmitAnswerInput(BaseModel):
    command: str = Field(description="The command to control the robot, e.g. 'move forward', 'turn left', 'pick up object'.")
