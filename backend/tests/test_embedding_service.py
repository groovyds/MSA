import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock
import numpy as np

from app.services.embedding_service import create_embeddings, get_similar_chunks
from app.db.models import Presentation, PresentationEmbedding

# Test data
TEST_PRESENTATION_ID = 1
TEST_FILE_PATH = "/tmp/test_presentation.pptx"
TEST_QUERY = "What is this presentation about?"


@pytest.fixture
def mock_db_session():
    """Fixture to mock DB session for embedding service tests."""
    mock_session = MagicMock()
    
    # Mock presentation
    mock_presentation = MagicMock(spec=Presentation)
    mock_presentation.id = TEST_PRESENTATION_ID
    mock_presentation.file_path = TEST_FILE_PATH
    
    # Mock presentation embedding
    mock_embedding = MagicMock(spec=PresentationEmbedding)
    mock_embedding.text = "This is a test chunk from the presentation about AI."
    mock_embedding.chunk_index = 0
    
    # Configure mock query results
    mock_session.query.return_value.filter.return_value.first.return_value = mock_presentation
    
    # For similarity search
    mock_result = [(mock_embedding, 0.15)]  # tuple of (embedding_obj, distance)
    mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_result
    
    return mock_session


@pytest.fixture
def mock_openai_client():
    """Fixture to mock OpenAI client responses."""
    with patch("app.services.embedding_service.client") as mock_client:
        # Mock embedding response
        mock_embedding_data = MagicMock()
        mock_embedding_data.embedding = [0.1] * 1536  # Mock 1536-dimensional vector
        
        mock_response = MagicMock()
        mock_response.data = [mock_embedding_data]
        
        mock_client.embeddings.create.return_value = mock_response
        yield mock_client


@pytest.fixture
def mock_text_processor():
    """Fixture to mock text processing functions."""
    with patch("app.services.embedding_service.extract_text_from_presentation") as mock_extract:
        with patch("app.services.embedding_service.chunk_text") as mock_chunk:
            mock_extract.return_value = "This is test text extracted from the presentation."
            mock_chunk.return_value = ["Chunk 1 text.", "Chunk 2 text.", "Chunk 3 text."]
            yield (mock_extract, mock_chunk)


def test_create_embeddings(mock_db_session, mock_openai_client, mock_text_processor):
    """Test creating embeddings for a presentation."""
    # Execute the function
    result = create_embeddings(TEST_FILE_PATH, TEST_PRESENTATION_ID, mock_db_session)
    
    # Verify text processing
    mock_text_processor[0].assert_called_once_with(TEST_FILE_PATH)
    mock_text_processor[1].assert_called_once()
    
    # Verify OpenAI API calls
    assert mock_openai_client.embeddings.create.call_count == 3  # One call per chunk
    
    # Verify DB operations
    assert mock_db_session.add.call_count == 3  # One add per chunk
    mock_db_session.commit.assert_called_once()
    
    # Verify result
    assert len(result) == 3  # Three chunks
    for item in result:
        assert "embedding" in item
        assert "text" in item
        assert "chunk_index" in item


def test_get_similar_chunks(mock_db_session, mock_openai_client):
    """Test finding similar chunks using vector similarity search."""
    # Execute the function
    result = get_similar_chunks(TEST_QUERY, TEST_PRESENTATION_ID, mock_db_session, top_k=1)
    
    # Verify OpenAI API call for query embedding
    mock_openai_client.embeddings.create.assert_called_once()
    
    # Verify DB operations
    mock_db_session.query.assert_called()
    
    # Verify result
    assert len(result) == 1
    assert "text" in result[0]
    assert "similarity" in result[0]
    assert "chunk_index" in result[0]
    assert result[0]["similarity"] == pytest.approx(0.85)  # 1 - distance