from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from typing import List

from ..db.database import get_async_db
from ..db.models import ChatHistory, Presentation
from ..schemas.chat import ChatMessage, ChatResponse
from ..services.chat_service_2 import generate_response

router = APIRouter()

@router.post("/message", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    db: AsyncSession = Depends(get_async_db)
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
        stmt = select(Presentation).where(Presentation.id == message.presentation_id)
        result = await db.execute(stmt)
        presentation = result.scalar_one_or_none()

        if not presentation:
            raise HTTPException(
                status_code=404,
                detail=f"Presentation {message.presentation_id} not found"
            )
        
        # Generate response using the chat service
        response_data = await generate_response(
            message = message.content,
            presentation_id=message.presentation_id,
            user_id=message.user_id,    # pass user_id
            db=db,                      # pass db session
            max_context_chunks=5        # pass max_context_chunks
        )
        response_text = response_data["response"] if isinstance(response_data, dict) else response_data

        # Save the chat history
        chat_history = ChatHistory(
            user_id=message.user_id,
            presentation_id=message.presentation_id,
            message=message.content,
            response=response_text
        )
        db.add(chat_history)
        await db.commit()
        await db.refresh(chat_history)
        
        return ChatResponse(
            message=message.content,
            response=response_text,
            created_at=chat_history.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback() # async rollback db
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=List[ChatResponse])
async def get_chat_history(
    user_id: str,
    presentation_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db)
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
    try:
        # Verify presentation exists - Async
        stmt = select(Presentation).where(Presentation.id == presentation_id)
        result = await db.execute(stmt)
        presentation = result.scalar_one_or_none()
        
        if not presentation:
            raise HTTPException(
                status_code=404,
                detail=f"Presentation {presentation_id} not found"
            )
        
        # Get chat history - Async 
        stmt = await select(ChatHistory).where(
            ChatHistory.user_id == user_id,
            ChatHistory.presentation_id == presentation_id
            ).order_by(ChatHistory.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        chat_history = result.scalars().all()
        
        return [
            ChatResponse(
                message=chat.message,
                response=chat.response,
                created_at=chat.created_at
            )
            for chat in chat_history
        ] 

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))