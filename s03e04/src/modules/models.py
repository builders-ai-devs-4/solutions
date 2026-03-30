from pydantic import BaseModel, Field

class ConnectionsRequest(BaseModel):
    params: str


class ConnectionsResponse(BaseModel):
    output: str
