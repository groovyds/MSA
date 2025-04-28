from pydantic import BaseModel
from datetime import datetime

class ChatMessage(BaseModel):
    """Schema for incoming chat messages."""
    user_id: str
    presentation_id: int
    content: str

class ChatResponse(BaseModel):
    """Schema for chat responses."""
    message: str
    response: str
    created_at: datetime 