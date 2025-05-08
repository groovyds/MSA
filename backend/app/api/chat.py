from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from typing import List

from ..db.database import get_db
from ..db.models import ChatHistory, Presentation
from ..schemas.chat import ChatMessage, ChatResponse
from ..services.chat_service import generate_response

router = APIRouter()

@router.post("/message", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    db: Session = Depends(get_db)
):
    """
    Process a chat message and generate a response.
    
    Args:
        message: The chat message to process
        db: Database session
        
    Returns:
        ChatResponse: The generated response
        
    Raises:
        HTTPException: If the presentation is not found or other errors occur
    """
    try:
        # Verify presentation exists
        presentation = db.query(Presentation)\
            .filter(Presentation.id == message.presentation_id)\
            .first()
        if not presentation:
            raise HTTPException(
                status_code=404,
                detail=f"Presentation {message.presentation_id} not found"
            )
        
        # Generate response using the chat service
        response = await generate_response(
            message.content,
            presentation_id=message.presentation_id
        )
        
        # Save the chat history
        chat_history = ChatHistory(
            user_id=message.user_id,
            presentation_id=message.presentation_id,
            message=message.content,
            response=response
        )
        db.add(chat_history)
        db.commit()
        db.refresh(chat_history)
        
        return ChatResponse(
            message=message.content,
            response=response,
            created_at=chat_history.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=List[ChatResponse])
def get_chat_history(
    user_id: str,
    presentation_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get chat history for a specific user and presentation.
    
    Args:
        user_id: ID of the user
        presentation_id: ID of the presentation
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List[ChatResponse]: List of chat messages and responses
        
    Raises:
        HTTPException: If the presentation is not found
    """
    # Verify presentation exists
    presentation = db.query(Presentation)\
        .filter(Presentation.id == presentation_id)\
        .first()
    if not presentation:
        raise HTTPException(
            status_code=404,
            detail=f"Presentation {presentation_id} not found"
        )
    
    # Get chat history
    chat_history = db.query(ChatHistory)\
        .filter(
            ChatHistory.user_id == user_id,
            ChatHistory.presentation_id == presentation_id
        )\
        .order_by(ChatHistory.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return [
        ChatResponse(
            message=chat.message,
            response=chat.response,
            created_at=chat.created_at
        )
        for chat in chat_history
    ] 