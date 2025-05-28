import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock
import io
import time

from app.utils.text_processor import extract_text_from_presentation, chunk_text


@pytest.fixture
def sample_text():
    """Generate sample text for testing."""
    # Create a long text with multiple paragraphs for chunking tests
    paragraphs = []
    for i in range(20):
        paragraphs.append(f"This is paragraph {i+1}. It contains some text about testing. "
                         f"The paragraph number is {i+1}. This text will be used for chunking tests. "
                         f"We need to ensure that the chunking algorithm works correctly with "
                         f"various text lengths and structures.")
    
    return "\n\n".join(paragraphs)


@pytest.fixture
def mock_presentation_file():
    """Create a mock presentation file for testing."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as temp:
        # Write some binary content to simulate a PPTX file
        temp.write(b"PK\x03\x04\x14\x00\x00\x00\x08\x00mock presentation content")
        file_path = temp.name
    
    yield file_path
    
    # Clean up after test
    if os.path.exists(file_path):
        os.unlink(file_path)


@pytest.fixture
def mock_pptx():
    """Mock the python-pptx library for testing."""
    with patch("app.utils.text_processor.Presentation") as mock_pptx:
        # Mock presentation object
        mock_presentation = MagicMock()
        
        # Mock slides
        slide1 = MagicMock()
        slide2 = MagicMock()
        
        # Mock shapes with text frames
        shape1 = MagicMock()
        shape2 = MagicMock()
        shape3 = MagicMock()
        
        # Mock text frames with paragraphs
        text_frame1 = MagicMock()
        text_frame2 = MagicMock()
        text_frame3 = MagicMock()
        
        # Mock paragraphs with runs
        paragraph1 = MagicMock()
        paragraph2 = MagicMock()
        paragraph3 = MagicMock()
        
        # Mock text runs
        run1 = MagicMock()
        run1.text = "This is slide 1, shape 1 text."
        
        run2 = MagicMock()
        run2.text = "This is slide 1, shape 2 text."
        
        run3 = MagicMock()
        run3.text = "This is slide 2, shape 1 text."
        
        # Set up the structure
        paragraph1.runs = [run1]
        paragraph2.runs = [run2]
        paragraph3.runs = [run3]
        
        text_frame1.paragraphs = [paragraph1]
        text_frame2.paragraphs = [paragraph2]
        text_frame3.paragraphs = [paragraph3]
        
        shape1.text_frame = text_frame1
        shape2.text_frame = text_frame2
        shape3.text_frame = text_frame3
        
        slide1.shapes = [shape1, shape2]
        slide2.shapes = [shape3]
        
        mock_presentation.slides = [slide1, slide2]
        
        # Return the mock presentation for a file path
        mock_pptx.return_value = mock_presentation
        
        yield mock_pptx


def test_extract_text_from_presentation(mock_pptx, mock_presentation_file):
    """Test extracting text from a presentation file."""
    # Extract text
    text = extract_text_from_presentation(mock_presentation_file)
    
    # Check that the function called python-pptx correctly
    mock_pptx.assert_called_once_with(mock_presentation_file)
    
    # Verify the extracted text contains all the text from the mocked slides
    assert "This is slide 1, shape 1 text." in text
    assert "This is slide 1, shape 2 text." in text
    assert "This is slide 2, shape 1 text." in text


def test_chunk_text_with_long_text(sample_text):
    """Test chunking a long text into smaller segments."""
    # Try different max chunk sizes
    chunk_sizes = [200, 500, 1000]
    
    for max_chunk_size in chunk_sizes:
        chunks = chunk_text(sample_text, max_chunk_size=max_chunk_size)
        
        # Verify we have more than one chunk
        assert len(chunks) > 1
        
        # Check that no chunk exceeds the max size
        for chunk in chunks:
            assert len(chunk) <= max_chunk_size
        
        # Ensure all content is preserved (roughly)
        combined = ' '.join(chunks)
        # Remove whitespace to compare content only
        assert ' '.join(sample_text.split()) in ' '.join(combined.split())


def test_chunk_text_with_short_text():
    """Test chunking a short text that fits in one chunk."""
    short_text = "This is a short text that should fit in one chunk."
    
    chunks = chunk_text(short_text, max_chunk_size=1000)
    
    # Should have only one chunk
    assert len(chunks) == 1
    assert chunks[0] == short_text


def test_chunk_text_with_empty_text():
    """Test chunking an empty text."""
    chunks = chunk_text("", max_chunk_size=1000)
    
    # Should have no chunks
    assert len(chunks) == 0