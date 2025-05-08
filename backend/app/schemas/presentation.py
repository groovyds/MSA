from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime

class PresentationBase(BaseModel):
    """Base schema for presentation data."""
    filename: str = Field(..., min_length=1,
                          regex=r'^[\w\-\.]+$',
                          description="Name of the presentation file")
    user_id: str = Field(..., description="ID of the user who uploaded the presentation")

class PresentationCreate(PresentationBase):
    """Schema for creating a new presentation."""
    pass

class PresentationResponse(PresentationBase):
    """Schema for presentation response."""
    id: int = Field(..., description="Unique identifier for the presentation")
    upload_date: datetime = Field(..., description="When the presentation was uploaded")
    presentation_metadata: Optional[Dict] = Field(None, description="Additional metadata about the presentation")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True 