from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import func
from openai import OpenAI

import os
from typing import List, Dict, Any

from ..db.models import PresentationEmbedding, Presentation
from ..utils.text_processor import extract_text_from_presentation, chunk_text
from ..core.config import settings

# Load environment variables
load_dotenv(encoding='utf-16')

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_embeddings(file_path: str, presentation_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Create embeddings for a presentation file and store them in the database.
    
    Args:
        file_path: Path to the presentation file
        presentation_id: ID of the presentation
        db: Database session
        
    Returns:
        List of dictionaries containing embeddings and metadata
        
    Raises:
        Exception: If the presentation is not found or embeddings creation fails
    """
    try:
        # Verify presentation exists
        presentation = db.query(Presentation)\
            .filter(Presentation.id == presentation_id)\
            .first()
        if not presentation:
            raise Exception(f"Presentation {presentation_id} not found")
        
        # Extract text from the presentation
        text = extract_text_from_presentation(file_path)
        
        # Split text into chunks
        chunks = chunk_text(text)
        
        # Create embeddings for each chunk
        embeddings_data = []
        for i, chunk in enumerate(chunks):
            # Get embedding from OpenAI
            response = client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=chunk
            )
            
            # Extract the embedding vector
            embedding = response.data[0].embedding
            
            # Store the embedding with metadata
            embedding_record = PresentationEmbedding(
                presentation_id=presentation_id,
                chunk_index=i,
                text=chunk,
                embedding=embedding
            )
            db.add(embedding_record)
            embeddings_data.append({
                "embedding": embedding,
                "text": chunk,
                "chunk_index": i
            })
        
        db.commit()
        return embeddings_data
        
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to create embeddings: {str(e)}")

def get_similar_chunks(
    query: str,
    presentation_id: int,
    db: Session,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Find the most similar text chunks to a query using pgvector's similarity search.
    
    Args:
        query: The search query
        presentation_id: ID of the presentation to search in
        db: Database session
        top_k: Number of most similar chunks to return
        
    Returns:
        List of the most similar chunks with their similarity scores
        
    Raises:
        Exception: If the presentation is not found or search fails
    """
    try:
        # Verify presentation exists
        presentation = db.query(Presentation)\
            .filter(Presentation.id == presentation_id)\
            .first()
        if not presentation:
            raise Exception(f"Presentation {presentation_id} not found")
        
        # Get embedding for the query
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = response.data[0].embedding
        
        # Use pgvector's similarity search within the presentation
        similar_chunks = db.query(
            PresentationEmbedding,
            func.cosine_distance(PresentationEmbedding.embedding, query_embedding).label('distance')
        ).filter(
            PresentationEmbedding.presentation_id == presentation_id
        ).order_by('distance').limit(top_k).all()
        
        # Format results
        results = []
        for chunk, distance in similar_chunks:
            results.append({
                "text": chunk.text,
                "similarity": 1 - distance,  # Convert distance to similarity
                "chunk_index": chunk.chunk_index
            })
        
        return results
        
    except Exception as e:
        raise Exception(f"Failed to find similar chunks: {str(e)}") 