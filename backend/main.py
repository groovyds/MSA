"""Main FastAPI application module."""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.database import get_db, SessionLocal

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Marketing Strategist AI",
    description="AI-powered marketing strategy generation and analysis",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root() -> dict:
    """Root endpoint returning a welcome message.
    
    Returns:
        dict: A welcome message.
    """
    return {"message": "Welcome to Marketing Strategist AI API"}

@app.get("/test-db")
async def test_db(db: Session = Depends(get_db)) -> dict:
    """Test database connection endpoint.
    
    Args:
        db (Session): Database session.
        
    Returns:
        dict: Status of the database connection test.
    """
    try:
        # Try to execute a simple query
        result = db.execute(text("SELECT 1"))
        return {"status": "success", "message": "Database connection successful"}
    except Exception as e:
        return {"status": "error", "message": f"Database connection failed: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 