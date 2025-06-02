from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from typing import List, Dict, Any
import os

from .embedding_service import get_similar_chunks
from ..agents.base import PresentationAnalyst, ResearchAgent
from ..db.models import ChatHistory, Presentation
from ..core.config import settings
from ..agents.base import ChatAgent

# Load environment variables
load_dotenv(encoding='utf-16')

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

class ChatService:
    """Enhanced chat service with agent integration and RAG pipeline."""
    
    def __init__(self):
        self.presentation_analyst = PresentationAnalyst()
        self.research_agent = ResearchAgent()
        self.chat_agent = ChatAgent()
        
    async def generate_response(
        self,
        message: str,
        presentation_id: int,
        user_id: str,
        db: AsyncSession,
        max_context_chunks: int = 5,
        conversation_history_limit: int = 5
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive response using agents and RAG pipeline.
        
        Args:
            message: The user's message
            presentation_id: ID of the presentation being discussed
            user_id: ID of the user
            db: Database session
            max_context_chunks: Maximum number of similar chunks to include
            conversation_history_limit: Number of previous messages to include
            
        Returns:
            Dict containing response and metadata
        """
        try:
            # 1. Get presentation info - Async version
            stmt = select(Presentation).where(Presentation.id == presentation_id)
            result = await db.execute(stmt)
            presentation = result.scalar_one_or_none()
            
            if not presentation:
                raise Exception(f"Presentation {presentation_id} not found")
            
            # 2. Get conversation history for context
            conversation_context = await self._get_conversation_context(
                user_id, presentation_id, db, conversation_history_limit
            )
            
            # 3. Get relevant chunks using RAG
            similar_chunks = await get_similar_chunks(
                query=message,
                presentation_id=presentation_id,
                db=db,
                top_k=max_context_chunks
            )
            
            # 4. Determine intent and route to appropriate agent
            intent = await self._analyze_intent(message, conversation_context)
            
            # 5. Generate response based on intent
            if intent == "analysis":
                response_data = await self._handle_analysis_request(
                    message, similar_chunks, conversation_context, presentation
                )
            elif intent == "research":
                response_data = await self._handle_research_request(
                    message, similar_chunks, conversation_context, presentation
                )
            else:
                response_data = await self._handle_general_request(
                    message, similar_chunks, conversation_context, presentation
                )
            
            return response_data
            
        except Exception as e:
            await db.rollback() # async rollback
            raise Exception(f"Failed to generate response: {str(e)}")
    
    async def _get_conversation_context(
        self, 
        user_id: str, 
        presentation_id: int, 
        db: AsyncSession, 
        limit: int
    ) -> List[Dict[str, str]]:
        """Get recent conversation history for context."""
        try:
            stmt = select(ChatHistory).where(
                ChatHistory.user_id == user_id,
                ChatHistory.presentation_id == presentation_id
            ).order_by(ChatHistory.created_at.desc()).limit(limit)
            
            result = await db.execute(stmt)
            recent_chats = result.scalars().all()
            
            # Reverse to get chronological order
            context = []
            for chat in reversed(recent_chats):
                context.extend([
                    {"role": "user", "content": chat.message},
                    {"role": "assistant", "content": chat.response}
                ])
            
            return context
            
        except Exception:
            return []
    
    async def _analyze_intent(
        self, 
        message: str, 
        conversation_context: List[Dict[str, str]]
    ) -> str:
        """Analyze user intent to route to appropriate agent."""
        try:
            context_str = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in conversation_context[-4:]  # Last 2 exchanges
            ])
            
            intent_prompt = f"""
            Analyze the user's intent based on their message and conversation context.
            
            Conversation Context:
            {context_str}
            
            Current Message: {message}
            
            Classify the intent as one of:
            - analysis: User wants detailed analysis, insights, or strategic recommendations
            - research: User wants additional research or external information
            - general: General questions about the presentation content
            
            Return only the intent category (analysis/research/general):
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": intent_prompt}],
                temperature=0.1,
                max_tokens=50
            )
            
            intent = response.choices[0].message.content.strip().lower()
            return intent if intent in ["analysis", "research", "general"] else "general"
            
        except Exception:
            return "general"
    
    async def _handle_analysis_request(
        self,
        message: str,
        similar_chunks: List[Dict],
        conversation_context: List[Dict],
        presentation: Any
    ) -> Dict[str, Any]:
        """Handle analysis requests using the PresentationAnalyst agent."""
        
        # Prepare context for agent
        context = "\n\n".join([chunk["text"] for chunk in similar_chunks])
        
        # Build comprehensive prompt for analysis
        analysis_prompt = f"""
        You are an expert presentation analyst. Analyze the following presentation content 
        and provide strategic insights, recommendations, and detailed analysis.
        
        Presentation: {presentation.filename}
        
        Relevant Content:
        {context}
        
        User's Request: {message}
        
        Provide a comprehensive analysis including:
        1. Key insights from the content
        2. Strategic recommendations
        3. Potential opportunities or concerns
        4. Actionable next steps
        
        Response:
        """
        
        input_data = {
            "input": analysis_prompt,
            "context": context,
            "presentation_meta": {
                "filename": presentation.filename,
                "id": presentation.id
            }
        }
        
        # Use the PresentationAnalyst agent
        result = await self.presentation_analyst.process(input_data)
        
        return {
            "response": result.get("response", ""),
            "type": "analysis",
            "confidence": result.get("confidence", 0.8),
            "sources": [chunk["chunk_index"] for chunk in similar_chunks]
        }
    
    async def _handle_research_request(
        self,
        message: str,
        similar_chunks: List[Dict],
        conversation_context: List[Dict],
        presentation: Any
    ) -> Dict[str, Any]:
        """Handle research requests using the ResearchAgent."""
        
        context = "\n\n".join([chunk["text"] for chunk in similar_chunks])
        
        research_prompt = f"""
        You are a research assistant. Based on the presentation content and user's question,
        provide additional context, industry insights, and relevant information.
        
        Presentation Context:
        {context}
        
        User's Research Request: {message}
        
        Provide comprehensive research including:
        1. Industry context and trends
        2. Comparative analysis
        3. Supporting data or statistics
        4. External perspectives
        
        Response:
        """
        
        input_data = {
            "input": research_prompt,
            "context": context,
            "query": message
        }
        
        result = await self.research_agent.process(input_data)
        
        return {
            "response": result.get("response", ""),
            "type": "research",
            "confidence": result.get("confidence", 0.7),
            "sources": [chunk["chunk_index"] for chunk in similar_chunks]
        }
    
    async def _handle_general_request(
        self,
        message: str,
        similar_chunks: List[Dict],
        conversation_context: List[Dict],
        presentation: Any
    ) -> Dict[str, Any]:
        """Handle general questions about presentation content."""
        
        context = "\n\n".join([chunk["text"] for chunk in similar_chunks])
        
        # Build conversation history for context
        history_str = "\n".join([
            f"{msg['role'].title()}: {msg['content']}" 
            for msg in conversation_context[-6:]
        ])
        
        general_prompt = f"""
        You are a helpful AI assistant discussing a presentation. Use the provided context 
        to answer the user's question accurately and conversationally.
        
        Presentation: {presentation.filename}
        
        Recent Conversation:
        {history_str}
        
        Relevant Content:
        {context}
        
        User's Question: {message}
        
        Instructions:
        - Answer based on the presentation content
        - Be conversational and helpful
        - If you can't answer from the context, say so clearly
        - Reference specific parts of the presentation when relevant
        
        Response:
        """
        
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": general_prompt}],
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=800
        )
        
        return {
            "response": response.choices[0].message.content.strip(),
            "type": "general",
            "confidence": 0.9,
            "sources": [chunk["chunk_index"] for chunk in similar_chunks]
        }

# Create service instance
chat_service = ChatService()

async def generate_response(
    message: str,
    presentation_id: int,
    user_id: str = "default_user",
    db: AsyncSession = None,
    max_context_chunks: int = 5
) -> str:
    """
    Legacy function wrapper for backward compatibility.
    """
    result = await chat_service.generate_response(
        message=message,
        presentation_id=presentation_id,
        user_id=user_id,
        db=db,
        max_context_chunks=max_context_chunks
    )
    return result["response"]