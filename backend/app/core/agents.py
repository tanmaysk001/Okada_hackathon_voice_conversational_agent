from typing import Optional
from langgraph.checkpoint.redis import RedisSaver
from app.agent.graph import create_agent_graph
from app.core.config import settings

class AgentManager:
    """Manages LangGraph agent instances with proper dependency injection."""
    
    def __init__(self):
        self._checkpointer: Optional[RedisSaver] = None
        self._agent_graph = None
    
    @property
    def checkpointer(self) -> RedisSaver:
        """Get or create the Redis checkpointer."""
        if self._checkpointer is None:
            self._checkpointer = RedisSaver.from_url(settings.REDIS_URL)
        return self._checkpointer
    
    @property
    def agent_graph(self):
        """Get or create the agent graph with checkpointer."""
        if self._agent_graph is None:
            self._agent_graph = create_agent_graph(checkpointer=self.checkpointer)
        return self._agent_graph
    
    async def invoke_agent(self, input_data: dict, session_id: str):
        """Invoke the agent with proper session management."""
        config = {"configurable": {"thread_id": session_id}}
        return await self.agent_graph.ainvoke(input_data, config=config)

# Create a single instance for the application
agent_manager = AgentManager()