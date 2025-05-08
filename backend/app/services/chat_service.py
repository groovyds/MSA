from openai import OpenAI
from dotenv import load_dotenv

from typing import List, Dict, Any
import os

from sqlalchemy.orm import Session
from .embedding_service import get_similar_chunks
from app.core.config import settings

# Load environment variables
load_dotenv(encoding='utf-16')

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def generate_response(
    message: str,
    presentation_id: int,
    db: Session = None,
    max_context_chunks: int = 3
) -> str:
    """
    Generate a response to a chat message using relevant context from the presentation.
    
    Args:
        message: The user's message
        presentation_id: ID of the presentation being discussed
        db: Database session
        max_context_chunks: Maximum number of similar chunks to include in context
        
    Returns:
        str: The generated response
        
    Raises:
        Exception: If response generation fails
    """
    try:
        # Get relevant chunks from the presentation
        similar_chunks = get_similar_chunks(
            query=message,
            presentation_id=presentation_id,
            db=db,
            top_k=max_context_chunks
        )
        
        # Build context from similar chunks
        context = "\n\n".join([chunk["text"] for chunk in similar_chunks])
        
        # Build the prompt
        prompt = f"""You are a helpful AI assistant discussing a presentation. 
Use the following context from the presentation to answer the user's question.
If you cannot answer the question based on the context, say so.

Context from presentation:
{context}

User's question: {message}

Your response:"""
        
        # Generate response using OpenAI
        response = client.chat.completions.create(
            model= settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant discussing a presentation."},
                {"role": "user", "content": prompt}
            ],
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        raise Exception(f"Failed to generate response: {str(e)}") 