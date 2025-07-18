import redis
import json
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.core.config import settings
from app.core.session import get_session_history

router = APIRouter()

# Synchronous Redis client for this specific purpose
redis_client = redis.from_url(settings.REDIS_URL)

@router.get("/sessions", response_model=List[Dict[str, str]])
def get_all_sessions():
    """Retrieve +all chat session IDs and their titles from Redis."""
    try:
        session_keys = redis_client.keys("message_store:*")
        sessions = []
        for key in session_keys:
            session_id = key.decode('utf-8').split('message_store:')[1]
            
            # Fetch the first message to use as a title
            first_message_json = redis_client.lindex(key, 0)
            if first_message_json:
                first_message = json.loads(first_message_json.decode('utf-8'))
                # The message content is in a nested 'data' dictionary.
                # We can access it directly without another json.loads call.
                message_data = first_message.get('data', {})
                title = message_data.get('content', 'Untitled Chat')
            else:
                title = "Empty Chat"

            sessions.append({"session_id": session_id, "title": title[:100]}) # Truncate title
        
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not connect to Redis or fetch sessions: {e}")

@router.get("/sessions/{session_id}", response_model=List[Dict[str, Any]])
async def get_session_by_id(session_id: str):
    """Retrieve the full message history for a specific session ID."""
    try:
        history = get_session_history(session_id)
        messages = await history.aget_messages()
        return [message.dict() for message in messages]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not retrieve session history: {e}")

@router.delete("/sessions/{session_id}", status_code=200)

def delete_session_by_id(session_id: str):
    """Delete a specific chat session history from Redis."""
    try:
        # The key in Redis is prefixed by langchain
        key = f"message_store:{session_id}"
        result = redis_client.delete(key)
        if result == 0:
            # If the key doesn't exist, it's not a server error.
            # It could mean it was already deleted.
            raise HTTPException(status_code=404, detail="Session ID not found.")
        return {"message": f"Session {session_id} deleted successfully."}
    except HTTPException as e:
        raise e # Re-raise HTTPException
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not connect to Redis or delete session: {e}")
