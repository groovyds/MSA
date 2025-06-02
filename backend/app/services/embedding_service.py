from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from openai import AsyncOpenAI

import asyncio
import os
from typing import List, Dict, Any
import logging
import gc

from ..db.models import PresentationEmbedding, Presentation
from ..utils.text_processor import process_large_file_in_batches_with_metadata 
from ..core.config import settings

# Load environment variables
load_dotenv(encoding='utf-16')

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger = logging.getLogger(__name__)

async def create_embeddings_optimized(
        file_path: str,
        presentation_id: int,
        db: AsyncSession,
        chunk_batch_size: int = 500,    # OpenAI batch size
        db_batch_size: int = 1000,      # Database insert batch size
        max_concurrent: int = 5         # Concurrent API calls
) -> int:
    """
    Memory-optimized embedding creation for large files.
        
    Returns:
        Total number of embeddings created.
    """
    try:
        # Validate file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Presentation file not found: {file_path}")

        # Verify presentation exists
        result = await db.execute(
            select(Presentation).filter(Presentation.id == presentation_id)
        )
        presentation = result.scalar_one_or_none()
        if not presentation:
            raise ValueError(f"Presentation {presentation_id} not found")
        
        total_embeddings = 0

        # Process file in streaming chunks to avoid memory issues
        async for chunk_batch in process_large_file_in_batches_with_metadata(
            file_path=file_path,
            presentation_id=presentation_id,
            batch_size=chunk_batch_size,
            max_chunk_size=1000,
            overlap=100
        ):
            # Create embeddings for batch
            embedding_records = await create_embeddings_batch(
                chunk_batch, max_concurrent
            )

            # Insert to database in smaller batches
            await insert_embeddings_batch(db, embedding_records, db_batch_size)

            total_embeddings += len(embedding_records)
            logger.info(f"Processed batch: {total_embeddings} total embeddings.")

            # Force garbage collection to free memory
            gc.collect()
        
        logger.info(f"Successfully created {total_embeddings} embeddings")
        return total_embeddings
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create embeddings: {str(e)}")
        raise

async def create_embeddings_batch(
          chunk_batch: List[Dict[str, Any]],
          max_concurrent: int
) -> List[PresentationEmbedding]:
        """
        Create embeddings twith proper concurrency control and batching.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def create_embedding_with_limit(chunk_data):
             async with semaphore:
                  return await create_single_embedding_optimized(chunk_data)
        
        # Process with controlled concurrency
        tasks = [create_embedding_with_limit(chunk) for chunk in chunk_batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle results
        embedding_records = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Failed to create embedding: {result}")
                # Retry logic here?
                continue
            embedding_records.append(result)

        return embedding_records

async def create_single_embedding_optimized(
          chunk_data: Dict[str, Any]
) -> PresentationEmbedding:
        """Optimized single embedding creation with error handling."""
        max_retries = 3
        base_delay = 1

        for attempt in range(max_retries):
            try:
                response = await client.embeddings.create(
                    model=settings.EMBEDDING_MODEL,
                    input=chunk_data["text"],
                    encoding_format="float"
                )

                embedding = response.data[0].embedding
                  
                return PresentationEmbedding(
                    presentation_id=chunk_data["presentation_id"],
                    chunk_index=chunk_data["chunk_index"],
                    text=chunk_data["text"],
                    embedding=embedding
                  )
            
            except Exception as e:
                if attempt == max_retries - 1:
                    raise

                # Exponantial backoff with jitter
                delay = base_delay * (2 ** attempt) + (asyncio.get_event_loop().time() % 1)
                await asyncio.sleep(delay)

async def insert_embeddings_batch(
    db: AsyncSession,
    embedding_records: List[PresentationEmbedding],
    batch_size: int
):
    """Insert embeddings in smaller batches to avoid memory issues."""
    for i in range(0, len(embedding_records), batch_size):
        batch = embedding_records[i:i + batch_size]
        db.add_all(batch)
        await db.commit()

        # Clear session to free memory
        await db.close()

async def get_similar_chunks(
    query: str,
    presentation_id: int,
    db: AsyncSession,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Find the most similar text chunks to a query using pgvector's similarity search.
    
    Args:
        query: The search query
        presentation_id: ID of the presentation to search in
        db: Async database session
        top_k: Number of most similar chunks to return
        
    Returns:
        List of the most similar chunks with their similarity scores
        
    Raises:
        ValueError: If the presentation is not found
        Exception: If the search fails
    """
    try:
        # Verify presentation exists
        result = await db.execute(
        select(Presentation).filter(Presentation.id == presentation_id)
        )
        presentation = result.scalar_one_or_none()
        if not presentation:
            raise ValueError(f"Presentation {presentation_id} not found")
        
        # Get embedding for the query using the same model for creation
        response = await client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=query
        )
        query_embedding = response.data[0].embedding
        
        # Use pgvector's similarity search within the presentation
        result = await db.execute(
            select(
                PresentationEmbedding,
                func.cosine_distance(PresentationEmbedding.embedding, query_embedding).label('distance')
            ).filter(
                PresentationEmbedding.presentation_id == presentation_id
            ).order_by('distance').limit(top_k)
        )
        
        similar_chunks = result.all()

        # Format results
        results = []
        for chunk, distance in similar_chunks:
            results.append({
                "text": chunk.text,
                "similarity": 1 - distance,  # Convert distance to similarity
                "chunk_index": chunk.chunk_index,
                "presentation_id": presentation_id
            })
        
        logger.info(f"Found {len(results)} similar chunks for query in presentation {presentation_id}.")
        return results
        
    except Exception as e:
        logger.error(f"Failed to find similar chunks: {str(e)}")
        raise
