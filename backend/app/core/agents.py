# backend/app/core/agents.py

from typing import Optional
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from app.agent.graph import create_agent_graph
from app.core.config import settings
from langchain_core.runnables.history import RunnableWithMessageHistory
from app.core.session import get_session_history

class AgentManager:
    """Manages the LangGraph agent instance with its checkpointer."""
    
    def __init__(self):
        self._checkpointer: Optional[AsyncRedisSaver] = None
        self._agent_graph = None
        self._agent_with_history = None


    @property
    def checkpointer(self) -> AsyncRedisSaver:
        """Get the Redis checkpointer."""
        if self._checkpointer is None:
            raise RuntimeError("Checkpointer has not been set. It should be initialized during app startup.")
        return self._checkpointer

    def set_checkpointer(self, checkpointer: AsyncRedisSaver):
        """Sets the checkpointer instance from outside (e.g., during app startup)."""
        self._checkpointer = checkpointer
    
    @property
    def agent_graph(self):
        """Get or create the agent graph with the checkpointer."""
        if self._agent_graph is None:
            # Pass the checkpointer to the graph factory
            self._agent_graph = create_agent_graph(checkpointer=self.checkpointer)
        return self._agent_graph

    async def get_agent_with_history(self) -> RunnableWithMessageHistory:
        """Get or create the agent wrapped with session history management."""
        # This check is no longer strictly necessary if only called once, but good practice
        if self._agent_with_history is None:
            self._agent_with_history = RunnableWithMessageHistory(
                self.agent_graph,
                get_session_history,
                input_messages_key="messages",
                history_messages_key="messages", 
            )
        return self._agent_with_history

# Create a single, shared instance for the entire application
agent_manager = AgentManager()