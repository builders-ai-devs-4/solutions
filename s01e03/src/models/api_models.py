from pydantic import BaseModel

class OperatorsRequest(BaseModel):
    sessionID: str
    msg: str

class ResponseToOperator(BaseModel):
    msg: str

class CheckPackageRequest(BaseModel):
    apikey: str
    action: str = "check"
    packageid: str

class RedirectPackageRequest(BaseModel):
    apikey: str
    action: str = "redirect"
    packageid: str
    destination: str
    code: str