from langgraph.graph import Graph
from langchain_core.messages import HumanMessage, AIMessag
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from typing import Dict
from ..core.config import settings

class BaseAgent:
    """Base class for all agents in the system."""
    
    def __init__(
        self,
        model_name: str = settings.OPENAI_MODEL,
        temperature: float = settings.OPENAI_TEMPERATURE,
        max_tokens: int = 1000
    ):
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        self.prompt_template = self._create_prompt_template()
        
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Create the base prompt template for the agent."""
        return ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant specialized in analyzing marketing presentations."),
            ("human", "{input}")
        ])
    
    async def process(self, input_data: Dict) -> Dict:
        """Process input data and return results."""
        raise NotImplementedError
        
    def create_workflow(self) -> Graph:
        """Create the LangGraph workflow for this agent."""
        workflow = Graph()
        
        @workflow.node
        async def process_input(state: Dict) -> Dict:
            return await self.process(state)
            
        return workflow
        
class PresentationAnalyst(BaseAgent):
    """Agent specialized in analyzing PowerPoint presentations."""
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", """You are an expert in analyzing marketing presentations.
            Your task is to extract key insights, identify main themes, and provide
            strategic recommendations based on the presentation content."""),
            ("human", "{input}")
        ])
    
    async def process(self, input_data: Dict) -> Dict:
        """Process presentation content and return analysis."""
        # Implementation for presentation analysis
        pass

class ResearchAgent(BaseAgent):
    """Agent specialized in conducting additional research."""
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", """You are a research assistant specialized in marketing
            and business analysis. Your task is to provide additional context
            and insights based on the given topic."""),
            ("human", "{input}")
        ])
    
    async def process(self, input_data: Dict) -> Dict:
        """Process research query and return findings."""
        # Implementation for research
        pass 