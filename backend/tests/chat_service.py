import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json

from app.services.chat_service import generate_response
from app.services.embedding_service import get_similar_chunks


@pytest.fixture
def mock_embedding_service():
    """Mock the embedding service for testing."""
    with patch("app.services.chat_service.get_similar_chunks") as mock:
        mock.return_value = [
            {
                "text": "The presentation is about advanced AI models and their applications.",
                "similarity": 0.92,
                "chunk_index": 0
            },
            {
                "text": "We discuss the technical architecture of modern AI systems.",
                "similarity": 0.87,
                "chunk_index": 1
            },
            {
                "text": "The presentation includes implementation details and code examples.",
                "similarity": 0.82,
                "chunk_index": 2
            }
        ]
        yield mock


@pytest.fixture
def mock_openai_api():
    """Mock the OpenAI API for testing."""
    with patch("app.services.chat_service.client") as mock_client:
        # Create mock completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Based on the presentation, this is about advanced AI models and their applications in various domains."
        
        # Set up the mock for chat.completions.create
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        yield mock_client


@pytest.mark.asyncio
async def test_generate_response(mock_embedding_service, mock_openai_api):
    """Test generating a response based on a user query."""
    # Test data
    user_query = "What is this presentation about?"
    presentation_id = 1
    
    # Call the function
    response = await generate_response(user_query, presentation_id)
    
    # Verify the embedding service was called
    mock_embedding_service.assert_called_once_with(
        user_query, 
        presentation_id, 
        top_k=3  # Assuming top_k=3 is the default
    )
    
    # Verify OpenAI API was called
    mock_openai_api.chat.completions.create.assert_called_once()
    
    # Check the API was called with the right parameters
    call_args = mock_openai_api.chat.completions.create.call_args[1]
    assert "messages" in call_args
    assert call_args["messages"][0]["role"] == "system"
    assert call_args["messages"][1]["role"] == "user"
    
    # Verify the response matches what we expect
    assert response == "Based on the presentation, this is about advanced AI models and their applications in various domains."


@pytest.mark.asyncio
async def test_generate_response_without_similar_chunks(mock_embedding_service, mock_openai_api):
    """Test generating a response when no similar chunks are found."""
    # Configure mock to return empty list
    mock_embedding_service.return_value = []
    
    # Test data
    user_query = "What is this presentation about?"
    presentation_id = 1
    
    # Call the function
    response = await generate_response(user_query, presentation_id)
    
    # Verify the embedding service was called
    mock_embedding_service.assert_called_once()
    
    # Verify OpenAI API was called
    mock_openai_api.chat.completions.create.assert_called_once()
    
    # Check the API was called with the right parameters
    call_args = mock_openai_api.chat.completions.create.call_args[1]
    assert "messages" in call_args
    
    # Verify the response is still generated
    assert response == "Based on the presentation, this is about advanced AI models and their applications in various domains."


@pytest.mark.asyncio
async def test_generate_response_with_openai_error(mock_embedding_service):
    """Test handling OpenAI API errors."""
    # Test data
    user_query = "What is this presentation about?"
    presentation_id = 1
    
    # Mock OpenAI API error
    with patch("app.services.chat_service.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        
        # Call the function
        response = await generate_response(user_query, presentation_id)
        
        # Verify the embedding service was called
        mock_embedding_service.assert_called_once()
        
        # Verify the response is an error message
        assert "I'm sorry" in response
        assert "process your request" in response