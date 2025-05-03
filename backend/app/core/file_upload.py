from app.core.config import settings
import os

# File upload settings
MAX_UPLOAD_SIZE = settings.MAX_UPLOAD_SIZE
ALLOWED_EXTENSIONS = settings.ALLOWED_EXTENSIONS
UPLOAD_DIR = settings.UPLOAD_DIR
STATIC_DIR = settings.STATIC_DIR

# Ensure upload and static directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

def get_upload_settings():
    """Get the configured file upload settings."""
    return {
        "max_size": MAX_UPLOAD_SIZE,
        "allowed_extensions": ALLOWED_EXTENSIONS,
        "upload_dir": UPLOAD_DIR,
        "static_dir": STATIC_DIR
    } 