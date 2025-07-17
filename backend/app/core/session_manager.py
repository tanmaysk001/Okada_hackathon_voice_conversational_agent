import redis.asyncio as redis
from app.core.config import settings
from app.core.async_redis_chat_message_history import AsyncRedisChatMessageHistory

# Use an asynchronous Redis client
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def set_session_file_info(session_id: str, file_type: str, file_path: str = None):
    """Stores file information for a given session in Redis asynchronously."""
    key = f"session:{session_id}:file_info"
    value = {"file_type": file_type, "file_path": file_path}
    import json
    await redis_client.set(key, json.dumps(value))

async def get_session_file_info(session_id: str) -> dict:
    """Retrieves file information for a given session from Redis asynchronously."""
    key = f"session:{session_id}:file_info"
    result = await redis_client.get(key)
    if result:
        import json
        return json.loads(result)
    return None

def get_session_history(session_id: str) -> AsyncRedisChatMessageHistory:
    """
    Returns an instance of AsyncRedisChatMessageHistory for the given session ID.
    This allows for asynchronous operations on the chat history.
    """
    return AsyncRedisChatMessageHistory(session_id=session_id, url=settings.REDIS_URL)
