from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from typing import List
import os
import shutil
import logging
import uuid
import json

from ..db.database import get_db
from ..db.models import Presentation, PresentationEmbedding
from ..services.embedding_service import create_embeddings
from ..schemas.presentation import PresentationCreate, PresentationResponse

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Configure upload settings
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pptx", ".ppt", ".pdf"}

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

async def validate_file(file: UploadFile) -> bytes:
    """
    Validate the uploaded file.
    
    Args:
        file: The file to validate

    Returns:
        bytes: The content of the file
        
    Raises:
        HTTPException: If the file is invalid
    """
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // 1024 // 1024} MB"
        )
    return content


def save_file(file: UploadFile, content: bytes) -> str:
    """
    Accepts the content after validation and saves it to upload_dir.
    
    Args:
        file: object to save files from fastapi
        content: content from the validated file in bytes
        
    Returns:
        str: File path
        
    Raises:
        HTTPException: If the file cannot be saved
    """
    try:
        filename = os.path.basename(file.filename)
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        return file_path
    except Exception as e:
        raise HTTPException(status_code=500, detail="Could not save file")

def cleanup_file(file_path: str) -> None:
    """
    Clean up a file if it exists.
    
    Args:
        file_path: Path to the file to clean up
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.error(f"Failed to clean up file {file_path}: {str(e)}")

@router.post("/upload", response_model=PresentationResponse)
async def upload_presentation(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Upload a presentation file and create embeddings.
    (For small files up to 10MB)
    
    Args:
        file: The presentation file to upload
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        PresentationResponse: Information about the uploaded presentation
    """
    try:
        # Validate file
        file_content = await validate_file(file)
        
        # Save file
        file_path = save_file(file, file_content)

        # extract_metadata
        # logic here
        
        # Create presentation record  (Assuming file_path instead of file_data)
        presentation = Presentation(
            filename=file.filename,
            file_path=file_path,   # Updated from file_data
            user_id="default_user",  # TODO: Implement user authentication
            presentation_metadata={}  # TODO: Extract metadata from file
        )
        db.add(presentation)
        db.commit()
        db.refresh(presentation)
        
        # Create embeddings in background
        if background_tasks:
            background_tasks.add_task(create_embeddings, file_path, presentation.id, db)
        
        # Clean up the file after processing
        background_tasks.add_task(cleanup_file, file_path)
        
        return presentation
        
    except HTTPException:
        raise
    except IOError as e:
        logger.error(f"File operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="File processing error")
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
@router.post("/start-upload")
async def start_upload(filename: str):
    """
    Initiate a chunked upload process for large files.

    Args:
        filename: Name of the file being uploaded
        total_chunks: Total number of chunks expected

    Returns:
        dict: Contains unique upload_id
    """
    upload_id = str(uuid.uuid4())
    temp_dir = os.path.join(UPLOAD_DIR, upload_id)
    os.makedirs(temp_dir, exist_ok=True)
    metadata = {"filename": filename, "chunks": []}
    with open(os.path.join(temp_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f)
    return {"upload_id": upload_id}

@router.post("/upload_chunk")
async def upload_chunk(upload_id: str, chunk_index: int, chunk: UploadFile = File(...)):
    """
    Upload a single chunk of a large file.

    Args:
        upload_id: Unique identifier for the upload session
        chunk_index: Index of the chunk being uploaded
        chunk: The chunk data
    
    Returns:
        dict: Status of the chunk upload
    """
    temp_dir = os.path.join(UPLOAD_DIR, upload_id)
    metadata_path = os.path.join(temp_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=400, detail="Invalid upload ID")
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}")
    with open(chunk_path, "wb") as buffer:
        shutil.copyfileobj(chunk.file, buffer)
    metadata["chunks"].append(chunk_index)
    with open(metadata_path, "w") as f:
        json.dump(metadata, f)
    return {"status": "chunk uploaded"}

@router.post("/finalize-upload", response_model=PresentationResponse)
async def finalize_upload(
    upload_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Finalize a chunked upload, assemble the file, and process it.
    
    Args:
        upload_id: Unique identifier for the upload session
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        PresentationResponse: Information about the uploaded presentation
    """
    temp_dir = os.path.join(UPLOAD_DIR, upload_id)
    metadata_path = os.path.join(temp_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=400, detail="Invalid upload ID")
    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    # Organize file in order
    chunks = sorted(metadata["chunks"])
    if not chunks:
        raise HTTPException(status_code=400, detail="No chunks uploaded")
        
    # Assemble the file
    file_path = os.path.join(UPLOAD_DIR, metadata["filename"])
    with open(file_path, "wb") as final_file:
        for i in chunks:
            chunk_path = os.path.join(temp_dir, f"chunk_{i}")
            with open(chunk_path, "rb") as chunk_file:
                shutil.copyfileobj(chunk_file, final_file)

    # Create presenation
    presentation = Presentation(
        filename=metadata["filename"],
        file_path=file_path,
        user_id="default_user",
        presentation_metadata={}
    )
    db.add(presentation)
    db.commit()
    db.refresh(presentation)

    # Create embeddings in background
    if background_tasks:
        background_tasks.add_task(create_embeddings, file_path, presentation.id, db)

    # Clean up temporary directory
    background_tasks.add_task(shutil.rmtree, temp_dir)

    return presentation

@router.get("/", response_model=List[PresentationResponse])
def get_presentations(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get a list of presentations with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List[PresentationResponse]: List of presentations
    """
    presentations = db.query(Presentation).offset(skip).limit(limit).all()
    return presentations

@router.get("/{presentation_id}", response_model=PresentationResponse)
def get_presentation(
    presentation_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific presentation by ID.
    
    Args:
        presentation_id: ID of the presentation to retrieve
        db: Database session
        
    Returns:
        PresentationResponse: The requested presentation
        
    Raises:
        HTTPException: If the presentation is not found
    """
    presentation = db.query(Presentation).filter(Presentation.id == presentation_id).first()
    if not presentation:
        raise HTTPException(status_code=404, detail="Presentation not found")
    return presentation 