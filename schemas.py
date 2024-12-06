# schemas.py

from pydantic import BaseModel

class ChatCreate(BaseModel):
    pass  # No fields needed for chat creation

class MessageCreate(BaseModel):
    chat_id: int
    input: str

class MessageResponse(BaseModel):
    chat_id: int
    message_id: int
    response: str
