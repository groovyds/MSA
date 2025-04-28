# Marketing Strategist AI Assistant

An AI-powered application for analyzing PowerPoint presentations using LangGraph and GPT-4.

## Features
- PowerPoint presentation analysis
- Semantic search across presentations
- AI-powered chat interface
- Vector similarity search using pgvector

## Tech Stack
- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI, PostgreSQL with pgvector
- AI: LangGraph, GPT-4-mini
- Infrastructure: AWS EC2

## Project Structure
```
marketing-strategist-ai/
├── frontend/          # Next.js frontend application
├── backend/           # FastAPI backend application
├── infrastructure/    # AWS infrastructure setup
└── docs/             # Project documentation
```

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.9+
- PostgreSQL 15+
- AWS Account

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/marketing-strategist-ai.git
cd marketing-strategist-ai
```

2. Set up the frontend:
```bash
cd frontend
npm install
npm run dev
```

3. Set up the backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

4. Set up the database:
```bash
# Install PostgreSQL with pgvector extension
# Create database and run migrations
```

## Development

### Frontend Development
The frontend is built with Next.js and TypeScript. Key features:
- Modern UI with Tailwind CSS
- Real-time chat interface
- File upload and management
- Responsive design

### Backend Development
The backend is built with FastAPI. Key features:
- RESTful API endpoints
- PostgreSQL with pgvector integration
- LangGraph agent implementation
- File processing and storage

### AI Agent Development
The AI system uses LangGraph for:
- Presentation analysis
- Semantic search
- Context-aware responses
- Multi-agent collaboration

## Deployment

### AWS EC2 Setup
1. Launch EC2 instance
2. Configure security groups
3. Set up PostgreSQL with pgvector
4. Deploy frontend and backend
5. Configure Nginx and SSL

## Documentation
Detailed documentation can be found in the `docs/` directory:
- [Architecture Overview](docs/architecture.md)
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Development Guide](docs/development.md)

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details. 