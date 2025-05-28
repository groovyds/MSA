import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import tempfile
import shutil

from app.main import app
from app.db.database import get_db
from app.db.models import Base, Presentation
from app.core.config import settings

# Create an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create a temporary directory for file uploads
@pytest.fixture(scope="module")
def temp_upload_dir():
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    
    # Store original setting
    original_upload_dir = settings.UPLOAD_DIR
    
    # Override setting for tests
    settings.UPLOAD_DIR = temp_dir
    
    yield temp_dir
    
    # Clean up
    shutil.rmtree(temp_dir)
    
    # Restore setting
    settings.UPLOAD_DIR = original_upload_dir


@pytest.fixture(scope="module")
def test_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Add test data
    db = TestingSessionLocal()
    presentation = Presentation(
        id=1,
        filename="test_presentation.pptx",
        file_path="/tmp/test_presentation.pptx",
        user_id="test_user",
        presentation_metadata={}
    )
    db.add(presentation)
    db.commit()
    
    yield
    
    # Drop tables
    Base.metadata.drop_all(bind=engine)


# Override the dependency
@pytest.fixture
def client(test_db):
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides = {}


def test_health_check(client):
    """Test the API health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_database_connection(client):
    """Test that the database connection is working."""
    response = client.get("/api/presentations/1")
    assert response.status_code == 200
    presentation = response.json()
    assert presentation["id"] == 1
    assert presentation["filename"] == "test_presentation.pptx"


def test_invalid_presentation_id(client):
    """Test behavior with an invalid presentation ID."""
    response = client.get("/api/presentations/999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_invalid_file_upload(client, temp_upload_dir):
    """Test upload validation for invalid file types."""
    # Try to upload a non-allowed file type
    with open(__file__, "rb") as f:
        files = {"file": ("test.py", f, "text/x-python")}
        response = client.post("/api/presentations/upload", files=files)
    
    assert response.status_code == 400
    assert "file type not allowed" in response.json()["detail"].lower()


def test_large_file_validation(client, temp_upload_dir):
    """Test large file validation during chunked upload."""
    # Test with invalid chunk index
    start_data = {
        "filename": "large_test.pptx",
        "fileSize": 5 * 1024 * 1024,  # 5MB
        "totalChunks": 5
    }
    
    # Start upload
    start_response = client.post("/api/presentations/start-upload", json=start_data)
    assert start_response.status_code == 200
    upload_id = start_response.json()["upload_id"]
    
    # Test with invalid chunk index
    chunk_data = "test data".encode()
    files = {"chunk": ("chunk_0", io.BytesIO(chunk_data))}
    form_data = {
        "upload_id": upload_id,
        "chunk_index": 10,  # Invalid index
        "total_chunks": 5
    }
    
    response = client.post("/api/presentations/upload-chunk", 
                           files=files, 
                           data=form_data)
    assert response.status_code == 400
    assert "invalid chunk index" in response.json()["detail"].lower()