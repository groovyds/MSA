from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Marketing Strategist AI",
    description="AI-powered application for analyzing PowerPoint presentations",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.api import chat, presentations

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(presentations.router, prefix="/api/presentations", tags=["presentations"])

@app.get("/")
async def root():
    return {"message": "Welcome to Marketing Strategist AI API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 