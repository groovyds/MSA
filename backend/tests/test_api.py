import os
import pytest
import tempfile
import io
from fastapi.testclient import TestClient
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.main import app
from app.db.models import Presentation, PresentationEmbedding, ChatHistory
from app.services.embedding_service import create_embeddings
from app.services.chat_service import generate_response

# Create a test client
client = TestClient(app)

# Test data
TEST_USER_ID = "test_user"
TEST_PRESENTATION_ID = 1
TEST_FILENAME = "test_presentation.pptx"
TEST_CHUNK_SIZE = 1024 * 1024  # 1MB


@pytest.fixture
def mock_db_session():
    """Fixture to mock DB session for tests."""
    mock_session = MagicMock()
    
    # Mock presentation query results
    mock_presentation = MagicMock(spec=Presentation)
    mock_presentation.id = TEST_PRESENTATION_ID
    mock_presentation.filename = TEST_FILENAME
    mock_presentation.user_id = TEST_USER_ID
    mock_presentation.file_path = f"/tmp/{TEST_FILENAME}"
    mock_presentation.presentation_metadata = {}
    mock_presentation.upload_date = datetime.now()
    
    mock_session.query.return_value.filter.return_value.first.return_value = mock_presentation
    mock_session.query.return_value.offset.return_value.limit.return_value.all.return_value = [mock_presentation]
    
    return mock_session


@pytest.fixture
def mock_embedding_service():
    """Fixture to mock embedding service."""
    with patch("app.services.embedding_service.create_embeddings") as mock:
        mock.return_value = [
            {
                "embedding": [0.1] * 1536,
                "text": "Test chunk content",
                "chunk_index": 0
            }
        ]
        yield mock


@pytest.fixture
def mock_chat_service():
    """Fixture to mock chat service."""
    with patch("app.services.chat_service.generate_response") as mock:
        mock.return_value = "This is a test response from the AI."
        yield mock


@pytest.fixture
def test_presentation_file():
    """Create a temporary test presentation file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as temp:
        temp.write(b"Mock presentation content")
        temp_path = temp.name
    
    yield temp_path
    
    # Clean up
    if os.path.exists(temp_path):
        os.unlink(temp_path)


def test_get_presentations(mock_db_session):
    """Test getting a list of presentations."""
    with patch("app.api.presentations.get_db", return_value=mock_db_session):
        response = client.get("/api/presentations/")
        
        assert response.status_code == 200
        presentations = response.json()
        assert isinstance(presentations, list)
        assert len(presentations) >= 1
        assert presentations[0]["id"] == TEST_PRESENTATION_ID
        assert presentations[0]["filename"] == TEST_FILENAME


def test_get_presentation_by_id(mock_db_session):
    """Test getting a specific presentation by ID."""
    with patch("app.api.presentations.get_db", return_value=mock_db_session):
        response = client.get(f"/api/presentations/{TEST_PRESENTATION_ID}")
        
        assert response.status_code == 200
        presentation = response.json()
        assert presentation["id"] == TEST_PRESENTATION_ID
        assert presentation["filename"] == TEST_FILENAME
        assert presentation["user_id"] == TEST_USER_ID


def test_upload_presentation(mock_db_session, mock_embedding_service, test_presentation_file):
    """Test uploading a small presentation file."""
    with patch("app.api.presentations.get_db", return_value=mock_db_session):
        # Create file-like object for upload
        with open(test_presentation_file, "rb") as f:
            file_content = f.read()
        
        files = {"file": (TEST_FILENAME, io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
        
        response = client.post("/api/presentations/upload", files=files)
        
        assert response.status_code == 200
        result = response.json()
        assert result["filename"] == TEST_FILENAME
        
        # Verify DB operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()


def test_large_file_upload_workflow(mock_db_session, mock_embedding_service, test_presentation_file):
    """Test the chunked upload workflow for large files."""
    with patch("app.api.presentations.get_db", return_value=mock_db_session):
        # 1. Start upload
        start_data = {
            "filename": TEST_FILENAME,
            "fileSize": 5 * 1024 * 1024,  # 5MB
            "totalChunks": 5
        }
        
        start_response = client.post("/api/presentations/start-upload", json=start_data)
        assert start_response.status_code == 200
        upload_id = start_response.json()["upload_id"]
        
        # 2. Upload chunks
        with open(test_presentation_file, "rb") as f:
            file_content = f.read()
            
        # Simulate uploading 5 chunks
        for i in range(5):
            chunk_data = io.BytesIO(file_content)
            files = {"chunk": (f"chunk_{i}", chunk_data)}
            form_data = {
                "upload_id": upload_id,
                "chunk_index": i,
                "total_chunks": 5
            }
            
            chunk_response = client.post("/api/presentations/upload-chunk", 
                                         files=files, 
                                         data=form_data)
            assert chunk_response.status_code == 200
            
        # 3. Finalize upload
        finalize_response = client.post(f"/api/presentations/finalize-upload?upload_id={upload_id}")
        assert finalize_response.status_code == 200
        result = finalize_response.json()
        assert result["filename"] == TEST_FILENAME


def test_chat_workflow(mock_db_session, mock_chat_service):
    """Test the chat functionality for a presentation."""
    with patch("app.api.chat.get_db", return_value=mock_db_session):
        # 1. Send a message
        message_data = {
            "user_id": TEST_USER_ID,
            "presentation_id": TEST_PRESENTATION_ID,
            "content": "What is this presentation about?"
        }
        
        message_response = client.post("/api/chat/message", json=message_data)
        assert message_response.status_code == 200
        result = message_response.json()
        assert result["message"] == message_data["content"]
        assert result["response"] == "This is a test response from the AI."
        
        # 2. Get chat history
        history_response = client.get(f"/api/chat/history?user_id={TEST_USER_ID}&presentation_id={TEST_PRESENTATION_ID}")
        assert history_response.status_code == 200
        history = history_response.json()
        assert isinstance(history, list)
        assert len(history) >= 1
        assert history[0]["message"] == message_data["content"]