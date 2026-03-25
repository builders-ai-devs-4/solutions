
from pydantic import BaseModel, Field
from typing import Dict, Union, List, Any

class AnswerModel(BaseModel):
    """Model representing the final answer required to complete the task."""
    password: str = Field(..., description="The employee system password found in the emails.")
    date: str = Field(..., description="The planned attack date in YYYY-MM-DD format.")
    confirmation_code: str = Field(..., description="The confirmation code starting with SEC- (36 characters total).")

class SolutionUrlRequest(BaseModel):
    """Payload structure for submitting the final solution to the Central Command."""
    apikey: str = Field(..., description="Your API key for authentication.")
    task: str = Field(..., description="The name of the current task.")
    answer: AnswerModel = Field(..., description="The final answer object containing extracted data.")

class ActionDetails(BaseModel):
    """Details of a specific action available in the Mailbox API."""
    description: str = Field(..., description="Description of what the action does.")
    params: Union[Dict[str, str], List[Any]] = Field(
        ..., 
        description="Parameters required for the action. It is a dictionary for most actions, or an empty list for 'help'."
    )

class ApiHelpResponse(BaseModel):
    """Successful response model for the Mailbox API 'help' action."""
    ok: bool = Field(..., description="Status of the request. True if successful.")
    mode: str = Field(..., description="Current mode of the API (e.g., 'read_only').")
    description: str = Field(..., description="General description of the API.")
    actions: Dict[str, ActionDetails] = Field(..., description="Dictionary mapping action names to their details and parameters.")

class ApiErrorResponse(BaseModel):
    """Error response model for the Mailbox API."""
    ok: bool = Field(..., description="Status of the request. Always False in case of an error.")
    action: str = Field(..., description="The name of the action that caused the error.")
    error: str = Field(..., description="The detailed error message returned by the server.")