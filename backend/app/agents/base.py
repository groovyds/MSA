from langgraph.graph import StateGraph, END, START
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Dict, List, Any, Optional, TypedDict, Annotated
import operator
from ..core.config import settings
from ..services.embedding_service import get_similar_chunks
from ..db.models import Presentation

# State schema for the agent
class AgentState(TypedDict):
    messages: Annotated[List[Any], operator.add]
    context: Optional[str]
    query: str
    retrieved_docs: List[Document]
    analysis_type: str # What
    user_id: Optional[str] 
    presentation_id: Optional[int]
    db_session: Optional[AsyncSession]


class BaseAgent:
    """Enhanced base classs intergrated with pgvector and existing services."""
    
    def __init__(
        self,
        model_name: str = settings.OPENAI_MODEL,
        temperature: float = settings.OPENAI_TEMPERATURE,
        max_tokens: int = 1000,
    ):
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True  # Enable streaming for chat
        )
        self.prompt_template = self._create_prompt_template()

    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Base prompt template for all agents."""
        return ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant specialized in analyzing marketing presentations. )

            Use the following context from the presentation to answer questions:
             {context}

             If you don't have enough information in the context, say so clearly.
             Always be specific and reference relevant information form the presentations."""),
             ("human", "{query}")
             ])

    async def retrieve_context(
            self,
            query: str,
            presentation_id: int,
            db: AsyncSession,
            k: int = 5
    ) -> List[Document]:
        """Retrieve relevant documents using embedding service."""
        try:
            similar_chunks = await get_similar_chunks(
                query=query,
                presentation_id = presentation_id,
                db=db,
                top_k=k
            )

            docs = []
            for chunk in similar_chunks:
                doc = Document(
                    page_content=chunk["text"],
                    metadata={
                        "source": f"presentation_{presentation_id}",
                        "chunk_index": chunk["chunk_index"],
                        "similarity": chunk["similarity"],
                        "presentation_id": presentation_id
                    }
                )
                docs.append(doc)

            return docs
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return []
        
    def format_context(self, docs: List[Document]) -> str:
        """Format retrieved documents into context string."""
        if not docs:
            return "No relevant context found."
        
        context_parts = []
        for i, doc in enumerate(docs):
            chunk_index = doc.metadata.get('chunk_index', i)
            similarity = doc.metadata.get('similarity', 0)
            content = doc.page_content[:800]  # Limit content length
            context_parts.append(
                f"Chunk {chunk_index} (similarity: {similarity:.3f}):\n{content}"
            )
        
        return "\n\n".join(context_parts)
        
    def create_workflow(self) -> StateGraph:
        """Create LangGraph workflow for this agent."""
        workflow = StateGraph(AgentState)
        
        # Define workflow nodes
        workflow.add_node("retrieve", self.retrieve_node)
        workflow.add_node("analyze", self.analyze_node)
        workflow.add_node("generate", self.generate_node)
        
        # Define workflow edges
        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "analyze")
        workflow.add_edge("analyze", "generate")
        workflow.add_edge("generate", END)
        
        return workflow.compile()
        


    async def retrieve_node(self, state: AgentState) -> Dict:
        """Node for retrieving relevant context using pgvector."""
        query = state.get("query", "")
        presentation_id = state.get("presentation_id")
        db = state.get("db_session")

        if not presentation_id or not db:
            return {
                "context": " No presentation context available.",
                "retrieve_docs": []
            }
        
        docs = await self.retrieve_context(query, presentation_id, db)
        context = self.format_context(docs)

        return {
            "context": context,
            "retrieved_docs": docs
        }

    async def analyze_node(self, state: AgentState) -> Dict:
        """Node for analyzing the retrieved context."""
        # This can be overridden by subclasses for specific analysis
        return {}
    
    async def generate_node(self, state: AgentState) -> Dict:
        """Generate final response using LLM."""
        context = state.get("context", "")
        query = state.get("query", "")
        
        # Format the prompt with context and query
        messages = [
            ("system", f"""You are a helpful AI assistant specialized in analyzing marketing presentations.
            Use the following context from the presentation to answer questions:
            {context}

            If you don't have enough information in the context, say so clearly.
            Always be specific and reference relevant information form the presentations."""),
            ("human", query)
        ]
        
        # Generate response
        response = await self.llm.ainvoke(messages)
        
        return {
            "messages": [AIMessage(content=response.content)]
        }

class PresentationAnalyst(BaseAgent):
    """Agent specialized in analyzing PowerPoint presentations with RAG."""
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", """You are an expert marketing presentation analyst with access to a knowledge base of presentations.

            PRESENTATION CONTEXT:
            {context}

            Your expertise includes:
            1. Extracting key strategic insights and themes
            2. Identifying messaging strategies and positioning
            3. Providing actionable recommendations
            4. Comparing content with best practices
            5. Highlighting areas for improvement

            Always reference specific content from the presentation and provide strategic depth."""),
            ("human", "{query}")
        ])
    
    async def analyze_node(self, state: AgentState) -> Dict:
        """Enhanced analysis for presentation content."""
        docs = state.get("retrieved_docs", [])
        
        # Extract presentation-specific metadata
        presentation_info = []
        for doc in docs:
            metadata = doc.metadata
            if 'slide_number' in metadata:
                presentation_info.append({
                    'source': metadata.get('source', 'Unknown'),
                    'slide': metadata.get('slide_number'),
                    'title': metadata.get('slide_title', 'No title')
                })
        
        return {
            "analysis_type": "presentation_analysis",
            "presentation_info": presentation_info
        }

class ResearchAgent(BaseAgent):
    """Agent specialized in conducting research with web search capabilities."""
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", """You are a research assistant specialized in marketing and business analysis.

            PRESENTATION CONTEXT:
            {context}

            Your tasks:
            1. Provide additional context based on presentation content
            2. Find relevant market trends and insights
            3. Suggest competitive analysis points
            4. Recommend industry best practices
            5. Identify knowledge gaps that need further research

            Always connect your research back to the specific presentations and user's needs."""),
            ("human", "{query}")
        ])
    
    async def analyze_node(self, state: AgentState) -> Dict:
        """Research-focused analysis."""
        return {
            "analysis_type": "research_analysis",
            "research_focus": "industry_context"
        }


class ChatAgent:
    """Main chat interface agent that orchestrates other agents."""
    
    def __init__(self):
        self.presentation_analyst = PresentationAnalyst()
        self.research_agent = ResearchAgent()
        self.conversation_history = []
    
    async def chat(
            self,
            user_message: str,
            presentation_id: int,
            db: AsyncSession,
            user_id: Optional[str] = None
    ) -> str:
        """Main chat interface with agent routing."""
        # Determine which agent to use based on message content
        agent = self._route_to_agent(user_message)
        
        # Create state
        state = AgentState(
            messages=[HumanMessage(content=user_message)],
            query=user_message,
            context="",
            retrieved_docs=[],
            analysis_type="",
            user_id=user_id,
            presentation_id=presentation_id,
            db_session=db
        )
        
        # Run the workflow
        workflow = agent.create_workflow()
        result = await workflow.ainvoke(state)
        
        # Extract response
        response = result["messages"][-1].content
        
        # Update conversation history
        self.conversation_history.append({
            "user": user_message,
            "assistant": response,
            "timestamp": "now"  # Replace with actual timestamp
        })
        
        return response
    
    def _route_to_agent(self, message: str) -> BaseAgent:
        """Simple routing logic - can be enhanced with classification."""
        message_lower = message.lower()

        research_keywords = [
            "research", "trends", "market", "competitor", "industry", 
            "benchmark", "best practices", "comparison", "external"
            ]
        
        analysis_keywords = [
            "analyze", "insights", "strategy", "recommend", "improve",
            "strategic", "assessment", "evaluation", "deep dive"
            ]
        
        if any(keyword in message_lower for keyword in research_keywords):
            return self.research_agent
        elif any(keyword in message_lower for keyword in analysis_keywords):
            return self.presentation_analyst            
        else:
            return self.presentation_analyst
    
    async def stream_chat(self, user_message: str, user_id: Optional[str] = None):
        """Streaming chat interface for real-time responses."""
        agent = self._route_to_agent(user_message)
        
        state = AgentState(
            messages=[HumanMessage(content=user_message)],
            query=user_message,
            context="",
            retrieved_docs=[],
            analysis_type="",
            user_id=user_id,
            presentation_id=presentation_id,
            db_session=db
        )
        
        workflow = agent.create_workflow()
        
        # Stream the response
        async for chunk in workflow.astream(state):
            if "messages" in chunk and chunk["messages"]:
                yield chunk["messages"][-1].content