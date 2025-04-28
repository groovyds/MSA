# -*- coding: utf-8 -*-
import os
from os.path import join, dirname
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Presentation
from urllib.parse import urlparse

def load_env_file(env_path):
    """Load environment variables from file with different encodings.
    
    Args:
        env_path (str): Path to the .env file
        
    Returns:
        bool: True if file was successfully loaded, False otherwise
        
    This function tries to load the .env file using different encodings
    to handle potential encoding issues. It supports:
    - utf-8
    - utf-16
    - utf-16le
    - utf-16be
    - ascii
    """
    encodings = ['utf-8', 'utf-16', 'utf-16le', 'utf-16be', 'ascii']
    
    for encoding in encodings:
        try:
            with open(env_path, 'r', encoding=encoding) as f:
                content = f.read()
                for line in content.splitlines():
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            print(f"✅ Successfully loaded .env file with {encoding} encoding")
            return True
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"Error reading .env with {encoding}: {str(e)}")
            continue
    
    return False

def test_database_connection():
    """Test database connection and basic operations.
    
    This function:
    1. Loads environment variables from .env file
    2. Establishes database connection
    3. Creates database tables
    4. Tests basic CRUD operations
    5. Cleans up test data
    
    Returns:
        bool: True if all tests pass, False if any test fails
    """
    try:
        # Load environment variables
        backend_dir = dirname(dirname(dirname(__file__)))
        dotenv_path = join(backend_dir, '.env')
        print(f"Looking for .env at: {dotenv_path}")
        
        if not load_env_file(dotenv_path):
            print("❌ Error: Could not load .env file with any encoding")
            return False
            
        # Get database URL from environment variables
        DATABASE_URL = os.getenv("DATABASE_URL")
        
        if not DATABASE_URL:
            print("❌ Error: DATABASE_URL not found in environment variables")
            return False
            
        print(f"Using database URL: {DATABASE_URL}")
        
        # Parse and display connection details (excluding password for security)
        parsed = urlparse(DATABASE_URL)
        print(f"Connection details:")
        print(f"  - Database: {parsed.path[1:]}")
        print(f"  - Host: {parsed.hostname}")
        print(f"  - Port: {parsed.port}")
        print(f"  - User: {parsed.username}")
            
        # Create SQLAlchemy engine
        engine = create_engine(DATABASE_URL)
        
        # Test database connection
        with engine.connect() as connection:
            print("✅ Successfully connected to the database")
            
        # Create all tables defined in Base.metadata
        Base.metadata.create_all(bind=engine)
        print("✅ Successfully created tables")
        
        # Create a session factory and test session
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        print("✅ Successfully created database session")
        
        # Test inserting data
        test_presentation = Presentation(
            filename="test.pptx",
            user_id="123e4567-e89b-12d3-a456-426614174000"
        )
        session.add(test_presentation)
        session.commit()
        print("✅ Successfully inserted test data")
        
        # Clean up: delete test data
        session.delete(test_presentation)
        session.commit()
        print("✅ Successfully cleaned up test data")
        
        return True
        
    except Exception as e:
        # Print detailed error information
        print(f"❌ Error: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the test when script is executed directly
    test_database_connection() 