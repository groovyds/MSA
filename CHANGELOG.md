# Changelog

All notable changes to the Marketing Strategist AI Assistant project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [x] 2025-05-07

### Added
- Field description in schema>chat_schema, chatMessage-content.
- File size checking for file upload in presentations api.
- Logging for cleanup function>presentations in api.
- Filename checking with regex added to schemas for presentation.
- Logging for app startup in __init__
- Logging into requirements.txt TODO


## Changed
- Exporting "Base" is now dented out from init file of app
- In database models, changed file_Data and meta_data to be Optional.
- db/models changed filename to be unique, and changed user_id to index = True

## [x] 2025-04-25

### Added
- Initial project setup with Next.js frontend and FastAPI backend
- PostgreSQL with pgvector integration for semantic search
- LangGraph implementation for AI-powered analysis
- Basic file upload and processing functionality
- Real-time chat interface with GPT-4 integration
- Comprehensive application initialization in `__init__.py`
- Static file serving support
- Improved CORS configuration with fallback options
- Created file_upload.py to manage file upload settings and ensure the upload and static directories exist.
- Created vector_search.py to manage vector search settings.

### Changed
- Refactored database initialization for better maintainability
- Implemented automatic model discovery in database setup
- Improved error handling in database operations
- Removed redundant code and improved code organization
- Restructured application entry point and configuration
- Separated application configuration from execution in main.py

### Fixed
- Fixed memory leaks in file processing pipeline
- Resolved database connection pooling issues
- Addressed race conditions in concurrent file uploads
- Fixed authentication token expiration handling

### Security
- Implemented end-to-end encryption for file uploads
- Added rate limiting for API endpoints
- Enhanced input validation and sanitization
- Updated dependencies to latest secure versions

## [0.1.0] - 2025-04-20

### Technical Details
- Frontend: Next.js 14, TypeScript 5, Tailwind CSS 3
- Backend: FastAPI 0.109, Python 3.9
- Database: PostgreSQL 17 with pgvector
- AI: LangGraph, GPT-4-mini
- Infrastructure: TBD