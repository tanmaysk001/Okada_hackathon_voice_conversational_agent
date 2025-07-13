import redis
from app.core.config import settings

# Create a Redis client instance for general-purpose session management
# Use redis.from_url to correctly parse the Redis connection URL
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def set_session_file_info(session_id: str, file_type: str, file_path: str = None):
    """Stores file information for a given session in Redis."""
    key = f"session:{session_id}:file_info"
    value = {"file_type": file_type, "file_path": file_path}
    # Use json.dumps if storing complex dicts, but for this simple case, a string is fine.
    import json
    redis_client.set(key, json.dumps(value))

def get_session_file_info(session_id: str) -> dict:
    """Retrieves file information for a given session from Redis."""
    key = f"session:{session_id}:file_info"
    result = redis_client.get(key)
    if result:
        import json
        return json.loads(result)
    return None
