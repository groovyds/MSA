"""
Database package initialization
"""
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .database import engine, Base
from .models import *  # Import all models

def _get_required_tables():
    """
    Get all table names from SQLAlchemy metadata that are part of our models.
    Excludes any SQLAlchemy internal tables.
    """
    return [table.name for table in Base.metadata.tables.values()]

def _is_initialized():
    """
    Check if the database is already initialized by checking for the existence of tables
    and the pgvector extension.
    """
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        # Check if all required tables exist
        required_tables = _get_required_tables()
        tables_exist = all(table in existing_tables for table in required_tables)
        
        # Check if pgvector extension exists
        with engine.connect() as conn:
            result = conn.execute(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ).scalar()
            vector_extension_exists = result is not None
        
        return tables_exist and vector_extension_exists
    except OperationalError:
        return False

def init_db(db: Session = None):
    """
    Initialize the database if it hasn't been initialized yet.
    This includes creating tables and enabling the pgvector extension.
    
    Args:
        db: Optional database session
    """
    if not _is_initialized():
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Ensure pgvector extension is enabled
        with engine.connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.commit()

# Initialize the database when the package is imported
init_db() 