# from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

import os

from app.core.config import settings

# Load environment variables
load_dotenv(encoding="utf-16")

# Create base class for models
Base = declarative_base()

# Create SQLAlchemy engine using the database URL from settings
SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI

# Create engine
engine = create_async_engine(SQLALCHEMY_DATABASE_URL)

# Create session factory
AsyncSessionLocal = sessionmaker(
    autoclass=AsyncSession,
    autoflush=False,
    bind=engine
)

# def get_db():
#     """
#     Get a database session.
#     """
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close() 

async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session