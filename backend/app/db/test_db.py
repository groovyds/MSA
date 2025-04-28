# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent
sys.path.append(str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Presentation, PresentationEmbedding, ChatHistory
from dotenv import load_dotenv

def test_database_connection():
    try:
        # Load environment variables
        load_dotenv()
        DATABASE_URL = os.getenv("DATABASE_URL")
        
        if not DATABASE_URL:
            print("❌ Error: DATABASE_URL not found in environment variables")
            return False
            
        print(f"Using database URL: {DATABASE_URL}")
            
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Test connection
        with engine.connect() as connection:
            print("✅ Successfully connected to the database")
            
        # Create tables
        Base.metadata.create_all(bind=engine)
        print("✅ Successfully created tables")
        
        # Test session creation
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        print("✅ Successfully created database session")
        
        # Test basic operations
        test_presentation = Presentation(
            filename="test.pptx",
            user_id="123e4567-e89b-12d3-a456-426614174000"
        )
        session.add(test_presentation)
        session.commit()
        print("✅ Successfully inserted test data")
        
        # Clean up
        session.delete(test_presentation)
        session.commit()
        print("✅ Successfully cleaned up test data")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_database_connection() 