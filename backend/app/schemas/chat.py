from pydantic import BaseModel, Field
from datetime import datetime

class ChatMessage(BaseModel):
    """Schema for incoming chat messages."""
    user_id: str
    presentation_id: int
    content: str = Field(..., min_length=1, description="User's chat message")

class ChatResponse(BaseModel):
    """Schema for chat responses."""
    message: str
    response: str
    created_at: datetime 