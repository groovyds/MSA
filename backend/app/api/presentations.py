from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Form
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from typing import List
import os
import shutil
import logging
import uuid
import json
import datetime


from ..db.database import get_db, SessionLocal
from ..db.models import Presentation, PresentationEmbedding
from ..services.embedding_service import create_embeddings
from ..schemas.presentation import PresentationCreate, PresentationResponse
from ..core.config import settings # import settings not class

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Configure upload settings
UPLOAD_DIR = settings.UPLOAD_DIR
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE
ALLOWED_EXTENSIONS = settings.ALLOWED_EXTENSIONS

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

#  Create embeddings in background with separate session
def create_embeddings_task(file_path:str, presentation_id:int):
    """
    Background task to create embeddings with its own database session.
    """
    db = SessionLocal()
    try:
        create_embeddings(file_path, presentation_id, db)
    except Exception as e:
        logger.error(f"Failed to create embeddings: {str(e)}")
    finally:
        db.close()

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

@router.get("/check-upload")
async def check_upload(upload_id: str):
    """
    Check if an upload session exists.

    Args:
        upload_id: Unique identifier for the upload session

    Returns:
        dict: Status of the upload session
    """
    temp_dir = os.path.join(UPLOAD_DIR, upload_id)
    metadata_path = os.path.join(temp_dir, "metadata.json")

    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Upload session not found")
    
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    
    return {"status": "active", "metadata": metadata}

@router.post("/cleanup-abandoned-uploads")
async def cleanup_abandoned_uploads(background_tasks: BackgroundTasks):
    """
    Clean up abandoned upload sessions older than 24 hours.
    This endpoint should be called periodically via a cron job.
    
    Args:
        background_tasks: FastAPI background tasks
        
    Returns:
        dict: Status of the cleanup operation
    """
    def _cleanup_old_uploads():
        count = 0
        now = datetime.now().timestamp()
        max_age = 24 * 60 * 60  # 24 hours in seconds
        
        for item in os.listdir(UPLOAD_DIR):
            item_path = os.path.join(UPLOAD_DIR, item)
            
            # Skip regular files and only process directories
            if not os.path.isdir(item_path):
                continue
                
            # Check if it's an upload directory (has metadata.json)
            metadata_path = os.path.join(item_path, "metadata.json")
            if not os.path.exists(metadata_path):
                continue
                
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    
                # Check creation time
                created_time = metadata.get("created", 0)
                last_updated = metadata.get("lastUpdated", created_time)
                
                # Use the most recent timestamp
                timestamp = max(created_time, last_updated)
                
                if (now - timestamp) > max_age:
                    shutil.rmtree(item_path)
                    count += 1
            except Exception as e:
                logger.error(f"Error processing {item_path}: {str(e)}")
                
        return count
        
    background_tasks.add_task(_cleanup_old_uploads)
    
    return {"status": "Cleanup task scheduled"}
                    
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
            file_size=len(file_content), # added
            user_id="default_user",  # TODO: Implement user authentication
            presentation_metadata={}  # TODO: Extract metadata from file
        )
        db.add(presentation)
        db.commit()
        db.refresh(presentation)
        
        # Create embeddings in background
        if background_tasks:
            background_tasks.add_task(create_embeddings_task, file_path, presentation.id)
        
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
async def start_upload(request: dict):
    """
    Initiate a chunked upload process for large files.

    Args:
        request: Dict containing filename, fileSize, totalChunks

    Returns:
        dict: Contains unique upload_id
    """

    # Validate the request
    required_fields = ["filename", "fileSize", "totalChunks"]
    for field in required_fields:
        if field not in request:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
    # Extract fields
    filename = request["filename"]
    file_size = request["fileSize"]
    total_chunks = request["totalChunks"]    

    # Validate file extension
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Create upload ID and temp directory
    upload_id = str(uuid.uuid4())
    temp_dir = os.path.join(UPLOAD_DIR, upload_id)
    os.makedirs(temp_dir, exist_ok=True)

    # Create metadata file
    metadata = {
        "filename": filename,
        "fileSize": file_size,
        "totalChunks": total_chunks,
        "chunks": [],
        "created": int(datetime.now().timestamp())
    }

    with open(os.path.join(temp_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f)
        
    return {"upload_id": upload_id}

@router.post("/upload-chunk")
async def upload_chunk(
    chunk: UploadFile = File(...),
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...)
):
    """
    Upload a single chunk of a large file.

    Args:
        chunk: The chunk data
        upload_id: Unique identifier for the upload session
        chunk_index: Index of the chunk being uploaded
        total_chunks: Total number of chunks expected
    
    Returns:
        dict: Status of the chunk upload
    """

    # Validate upload_id format
    try:
        uuid_obj = uuid.UUID(upload_id)
        if str(uuid_obj) != upload_id:
            raise HTTPException("Invalid UUID format")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID format")

    # Check if temp directory exists
    temp_dir = os.path.join(UPLOAD_DIR, upload_id)
    metadata_path = os.path.join(temp_dir, "metadata.json")

    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=400, detail="Upload session not found")
    
    # Load metadata
    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    # Validate chunk index
    if chunk_index < 0 or chunk_index >= metadata["totalChunks"]:
        raise HTTPException(status_code=400, detail="Invalid chunk index")
    
    # Save chunk
    chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}")

    try:
        with open(chunk_path, "wb") as buffer:
            shutil.copyfileobj(chunk.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save chunk: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save chunk")
    
    # Update metadata
    if chunk_index not in metadata["chunks"]:
        metadata["chunks"].append(chunk_index)
        metadata["lastUpdated"] = int(datetime.now().timestamp())

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

    return {
        "status": "chunk uploaded",
        "chunksReceived": len(metadata["chunks"]),
        "totalChunks": metadata["totalChunks"]
    }

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

    try:
        uuid_obj = uuid.UUID(upload_id)
        if str(uuid_obj) != upload_id:
            raise ValueError("Invalid UUID format")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID format")
    
    # Check if temp directory exists
    temp_dir = os.path.join(UPLOAD_DIR, upload_id)
    metadata_path = os.path.join(temp_dir, "metadata.json")

    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Invalid upload ID")
    
    # Load metadata
    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    # Verify all chunks were received
    expected_chunks = set(range(metadata["totalChunks"]))
    received_chunks = set(metadata["chunks"])

    if expected_chunks != received_chunks:
        missing_chunks = expected_chunks - received_chunks
        raise HTTPException(
            status_code=400, 
            detail=f"Incomplete upload. Missing chunks: {list(missing_chunks)[:10]}..."
        )

    # Assemble the file using a streaming approach to handle large files
    file_path = os.path.join(UPLOAD_DIR, metadata["filename"])

    # This reads each chunk into memory one by one
    try:
        with open(file_path, "wb") as final_file:
            for i in sorted(metadata["chunks"]):
                chunk_path = os.path.join(temp_dir, f"chunk_{i}")
                with open(chunk_path, "rb") as chunk_file:
                    # Copy in smaller blocks to avoid memory issues
                    shutil.copyfileobj(chunk_file, final_file, 1024 * 1024) # 1MB buffer
    except Exception as e:
        logger.error(f"Failed to assemble file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to assemble file")

    # Create presenation
    try:
        presentation = Presentation(
            filename=metadata["filename"],
            file_path=file_path,
            file_size=metadata["fileSize"],
            user_id="default_user",
            presentation_metadata={}
        )
        db.add(presentation)
        db.commit()
        db.refresh(presentation)
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        # Clean up the assembled file if database operation fails
        cleanup_file(file_path)
        raise HTTPException(status_code=500, detail="Database error")

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