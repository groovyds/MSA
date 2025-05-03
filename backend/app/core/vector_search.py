from app.core.config import settings

# Vector search settings
VECTOR_DIMENSION = settings.VECTOR_DIMENSION
SIMILARITY_THRESHOLD = settings.SIMILARITY_THRESHOLD

def get_vector_settings():
    """Get the configured vector search settings."""
    return {
        "dimension": VECTOR_DIMENSION,
        "similarity_threshold": SIMILARITY_THRESHOLD
    } 