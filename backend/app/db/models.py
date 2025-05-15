"""Database models for the application."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary, Text, ARRAY, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid
from sqlalchemy.orm import relationship, Mapped, mapped_column

from typing import List, Optional

Base = declarative_base()

class Presentation(Base):
    """Model for storing PowerPoint presentations and their metadata.
    
    Attributes:
        id (int): Primary key.
        filename (str): Name of the presentation file.
        upload_date (datetime): When the presentation was uploaded.
        file_path (str): File path to the presentation file.
        file_size (int): Size of the file in bytes.
        presentation_metadata (dict): JSON metadata about the presentation.
        user_id (str): ID of the user who uploaded the presentation.
        embeddings (List[PresentationEmbedding]): Related embeddings.
    """
    __tablename__ = "presentations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String, index=True)
    upload_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    file_path: Mapped[Optional[str]] = mapped_column(String)
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    presentation_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    user_id: Mapped[str] = mapped_column(String, index=True)
    
    # Relationship with embeddings
    embeddings: Mapped[List["PresentationEmbedding"]] = relationship(
        "PresentationEmbedding", 
        back_populates="presentation",
        cascade="all, delete-orphan"
    )

class PresentationEmbedding(Base):
    """Model for storing vector embeddings of presentation content.
    
    Attributes:
        id (int): Primary key.
        presentation_id (int): Foreign key to the presentation.
        chunk_index (int): Index of the chunk in the presentation.
        text (str): The text content that was embedded.
        embedding (Vector): The vector embedding of the text.
        presentation (Presentation): Related presentation.
    """
    __tablename__ = "presentation_embeddings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    presentation_id: Mapped[int] = mapped_column(Integer, ForeignKey("presentations.id"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Vector] = mapped_column(Vector(1536))
    
    # Relationship with presentation
    presentation: Mapped["Presentation"] = relationship(
        "Presentation", 
        back_populates="embeddings"
    )

class ChatHistory(Base):
    """Model for storing chat history.
    
    Attributes:
        id (int): Primary key.
        presentation_id (int): Foreign key to the presentation.
        user_id (str): ID of the user who sent the message.
        message (str): The user's message.
        response (str): The AI's response.
        created_at (datetime): When the message was created.
    """
    __tablename__ = "chat_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    presentation_id: Mapped[int] = mapped_column(Integer, ForeignKey("presentations.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    response: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now()) 