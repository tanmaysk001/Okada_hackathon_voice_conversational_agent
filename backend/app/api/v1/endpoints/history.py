# backend/app/api/v1/endpoints/history.py

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.services import persistent_history_service
from app.services.database_service import get_database

router = APIRouter()

@router.get("/sessions/{user_email}", response_model=List[Dict[str, str]])
async def get_user_sessions(user_email: str):
    """
    Retrieve all unique chat sessions for a specific user from MongoDB.
    """
    try:
        history_collection = await persistent_history_service.get_history_collection()
        
        pipeline = [
            {"$match": {"user_email": user_email, "session_id": {"$exists": True, "$ne": None}}},
            {"$sort": {"updated_at": -1}},
            {"$group": {
                "_id": "$session_id",
                "title": {"$first": {"$arrayElemAt": ["$messages.content", 0]}}
            }}
        ]
        
        sessions = []
        async for doc in history_collection.aggregate(pipeline):
            sessions.append({
                "session_id": doc["_id"],
                "title": doc.get("title", "Untitled Chat")[:100]
            })
            
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not fetch sessions from MongoDB: {e}")

@router.get("/session/{session_id}", response_model=List[Dict[str, Any]])
async def get_session_by_id(session_id: str, user_email: str):
    """
    Retrieve the full message history for a specific session ID and user email from MongoDB.
    """
    try:
        history = await persistent_history_service.get_conversation_history(user_email, session_id)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not retrieve session history: {e}")

@router.delete("/session/{session_id}", status_code=200)
async def delete_session_by_id(session_id: str, user_email: str):
    """
    Delete a specific chat session history from MongoDB for a given user.
    """
    try:
        history_collection = await persistent_history_service.get_history_collection()
        result = await history_collection.delete_one({"user_email": user_email, "session_id": session_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Session not found for the given user.")
            
        return {"message": f"Session {session_id} for user {user_email} deleted successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not delete session: {e}")