# Architecture Overview

## System Architecture

The Marketing Strategist AI application follows a modern, scalable architecture with the following components:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Next.js        │     │  FastAPI        │     │  PostgreSQL     │
│  Frontend       │◄───►│  Backend        │◄───►│  with pgvector  │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Frontend (Next.js)
- **Framework**: Next.js 14 with TypeScript
- **UI Components**: Tailwind CSS, Heroicons
- **State Management**: React Hooks, Zustand
- **API Communication**: Fetch API
- **File Handling**: react-dropzone

### Backend (FastAPI)
- **Framework**: FastAPI
- **Database**: PostgreSQL with pgvector extension
- **AI Integration**: LangGraph, GPT-4-mini
- **File Processing**: python-pptx
- **Authentication**: JWT

### Database (PostgreSQL)
- **Main Database**: PostgreSQL 17.4
- **Vector Storage**: pgvector extension
- **Schema**:
  - Presentations table
  - Presentation embeddings table
  - Chat history table

## Component Interaction

1. **File Upload Flow**:
   ```
   Frontend ─► Backend ─► File Processing ─► Vector Storage
   ```

2. **Chat Flow**:
   ```
   Frontend ─► Backend ─► LangGraph Agent ─► Vector Search ─► Response Generation
   ```

3. **Analysis Flow**:
   ```
   Frontend ─► Backend ─► PowerPoint Processing ─► AI Analysis ─► Results
   ```

## AI Agent Architecture

The system uses LangGraph for orchestrating multiple AI agents:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Presentation   │     │  Research       │     │  Synthesis      │
│  Analyst        │◄───►│  Agent          │◄───►│  Agent          │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Agent Responsibilities

1. **Presentation Analyst**
   - Extracts key insights from presentations
   - Identifies main themes and topics
   - Analyzes visual elements and structure

2. **Research Agent**
   - Conducts additional research on topics
   - Validates information
   - Provides context and background

3. **Synthesis Agent**
   - Combines insights and research
   - Generates coherent responses
   - Maintains conversation context

## Data Flow

1. **Presentation Processing**:
   - PowerPoint file uploaded
   - Text and metadata extracted
   - Content chunked and embedded
   - Vectors stored in PostgreSQL

2. **Query Processing**:
   - User query received
   - Query embedded
   - Similar content retrieved
   - Context provided to AI agents
   - Response generated and returned

## Security Considerations

1. **Authentication & Authorization**
   - JWT-based authentication
   - Role-based access control
   - Secure session management

2. **Data Protection**
   - Encrypted file storage
   - Secure database connections
   - Input validation and sanitization

3. **API Security**
   - Rate limiting
   - CORS configuration
   - Request validation

## Scalability Considerations

1. **Horizontal Scaling**
   - Stateless backend services
   - Load balancing with Nginx
   - Database connection pooling

2. **Performance Optimization**
   - Caching strategies
   - Batch processing
   - Asynchronous operations

3. **Resource Management**
   - Connection pooling
   - Memory management
   - File cleanup

## Monitoring and Logging

1. **Application Monitoring**
   - Performance metrics
   - Error tracking
   - Usage analytics

2. **System Monitoring**
   - Resource utilization
   - Database performance
   - Network metrics

3. **Logging**
   - Application logs
   - Error logs
   - Audit trails

## Deployment Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  AWS EC2        │     │  AWS RDS        │     │  AWS S3         │
│  Instance       │◄───►│  PostgreSQL     │◄───►│  (Optional)     │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Infrastructure Components

1. **EC2 Instance**
   - Ubuntu 20.04 LTS
   - Nginx web server
   - Systemd services
   - SSL with Let's Encrypt

2. **RDS Instance**
   - PostgreSQL 15.3
   - Automated backups
   - Multi-AZ deployment
   - Security groups

3. **Optional S3 Storage**
   - File storage
   - Backup storage
   - Static asset hosting 