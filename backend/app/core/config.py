"""
Application configuration settings.

This module defines all configuration settings for the application using Pydantic's
BaseSettings. It loads environment variables and provides type-safe access to
configuration values.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Marketing Strategist AI"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    DOCS_URL: str = "/api/docs"
    REDOC_URL: str = "/api/redoc"

    # CORS Settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]  # React frontend URL
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]
    
    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "marketing_ai"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        return f"postgresql://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_SERVER')}/{values.get('POSTGRES_DB')}"

    # OpenAI Settings
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TEMPERATURE: float = 0.7

    # File Upload Settings
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = ["pptx", "pdf", "docx"]
    UPLOAD_DIR: str = "uploads"
    STATIC_DIR: str = "static"

    # JWT Settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Vector Search Settings
    VECTOR_DIMENSION: int = 1536  # OpenAI embedding dimension
    SIMILARITY_THRESHOLD: float = 0.7

    # API Router Settings
    CHAT_PREFIX: str = "/api/chat"
    PRESENTATIONS_PREFIX: str = "/api/presentations"

    class Config:
        case_sensitive = True
        env_file = ".env"

# Create settings instance
settings = Settings() 