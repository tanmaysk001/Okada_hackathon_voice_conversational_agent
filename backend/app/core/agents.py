# backend/app/core/agents.py

from typing import Optional
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from app.agent.graph import create_agent_graph

class AgentManager:
    """Manages the LangGraph agent instance with its checkpointer."""
    
    def __init__(self):
        self._checkpointer: Optional[AsyncRedisSaver] = None
        self._agent_graph = None

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
            # The checkpointer is attached here, making the graph stateful.
            self._agent_graph = create_agent_graph(checkpointer=self.checkpointer)
        return self._agent_graph

    def get_agent_with_history(self):
        """
        Returns the stateful agent graph. 
        The graph itself handles history via its built-in checkpointer.
        """
        # We simply return the compiled graph. It is already the "runnable with history".
        return self.agent_graph

# Create a single, shared instance for the entire application
agent_manager = AgentManager()