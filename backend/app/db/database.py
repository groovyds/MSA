from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables with UTF-16 encoding
load_dotenv(encoding='utf-16')

# Get database URL from environment variable
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Create engine with pgvector support
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def get_db():
    """
    Get a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize the database, including pgvector extension.
    """
    # Import all models here to ensure they are registered with SQLAlchemy
    from .models import Presentation, PresentationEmbedding
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Ensure pgvector extension is enabled
    with engine.connect() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit() 