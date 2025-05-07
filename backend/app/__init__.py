"""
Marketing Strategist AI Backend Application

This module initializes the FastAPI application and its core components.
It sets up database connections, configures middleware, and imports all necessary routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

import os
from typing import Optional

# Load environment variables
load_dotenv()

# Import core components
from app.core.config import settings
from app.db.database import SessionLocal
from app.db import init_db

# Import routers
from app.api import chat, presentations

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-powered application for analyzing PowerPoint presentations",
        version=settings.APP_VERSION,
        docs_url=settings.DOCS_URL,
        redoc_url=settings.REDOC_URL,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )

    # Mount static files
    app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

    # Include routers
    app.include_router(chat.router, prefix=settings.CHAT_PREFIX, tags=["chat"])
    app.include_router(presentations.router, prefix=settings.PRESENTATIONS_PREFIX, tags=["presentations"])

    @app.on_event("startup")
    async def startup_event():
        """Initialize database and other components on startup."""
        # Initialize database
        db = SessionLocal()
        try:
            init_db(db)
        finally:
            db.close()

    @app.get("/")
    async def root() -> dict:
        """Root endpoint.

        Returns:
            dict: A welcome message.
        
        """
        return {"message": f"Welcome to {settings.APP_NAME} API"}

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    return app

# Create the application instance
app = create_app()

# Export commonly used components
__all__ = [
    "app",
    "settings",
    "SessionLocal",
    "Base",
] 