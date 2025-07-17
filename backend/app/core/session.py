import redis.asyncio as redis
from app.core.config import settings
from langchain_core.messages import HumanMessage, AIMessage
from app.core.async_redis_chat_message_history import AsyncRedisChatMessageHistory

def get_session_history(session_id: str) -> AsyncRedisChatMessageHistory:
    """Get or create a Redis-backed chat history for the given session ID."""
    return AsyncRedisChatMessageHistory(session_id, url=settings.REDIS_URL)

async def add_session_message(session_id: str, role: str, content: str):
    """Add a message to the session history asynchronously."""
    history = get_session_history(session_id)
    if role == "user":
        message = HumanMessage(content=content)
    else:
        message = AIMessage(content=content)
    await history.aadd_messages([message])