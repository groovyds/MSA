from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from typing import List
import os
import shutil
import logging

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

def validate_file(file: UploadFile) -> None:
    """
    Validate the uploaded file.
    
    Args:
        file: The file to validate
        
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
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // 1024 // 1024} MB"
        )
    
    # Check file size
    try:
        content = file.file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // 1024 // 1024}MB"
            )
        file.file.seek(0)  # Reset file pointer
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not validate file")

def save_file(file: UploadFile) -> tuple[str, bytes]:
    """
    Save the uploaded file and return its path and content.
    
    Args:
        file: The file to save
        
    Returns:
        tuple: File path and binary content
        
    Raises:
        HTTPException: If the file cannot be saved
    """
    try:
        content = file.file.read()
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        return file_path, content
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
    
    Args:
        file: The presentation file to upload
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        PresentationResponse: Information about the uploaded presentation
    """
    try:
        # Validate file
        validate_file(file)
        
        # Save file
        file_path, file_content = save_file(file)
        
        # Create presentation record
        presentation = Presentation(
            filename=file.filename,
            file_data=file_content,
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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