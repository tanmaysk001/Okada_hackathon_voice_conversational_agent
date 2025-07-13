import redis.asyncio as redis
from app.core.config import settings

from langchain_community.chat_message_histories import RedisChatMessageHistory

def get_session_history(session_id: str) -> RedisChatMessageHistory:
    """Get or create a Redis-backed chat history for the given session ID."""
    # The session history will be stored in Redis, keyed by the session_id.
    # This ensures that chat history is persistent across application restarts.
    return RedisChatMessageHistory(session_id, url=settings.REDIS_URL)