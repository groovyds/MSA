"""
Main entry point for the Marketing Strategist AI application.
This file serves as the application runner and should be used to start the server.
"""

import uvicorn
from app import app

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 