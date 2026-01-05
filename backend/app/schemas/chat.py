from pydantic import BaseModel

class MessageRequest(BaseModel):
    message: str

class MessageResponse(BaseModel):
    reply: str
