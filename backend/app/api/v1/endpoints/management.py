import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.session import get_session_history
from app.services.vector_store import delete_documents_by_session_id

router = APIRouter()

class ResetRequest(BaseModel):
    session_id: str

class ResetResponse(BaseModel):
    message: str
    processing_duration: float

@router.post("/reset", response_model=ResetResponse)
async def reset_conversation(request: ResetRequest):
    """
    Clears the conversation memory from Redis and all associated RAG documents from ChromaDB.
    """
    start_time = time.time()
    
    try:
        # 1. Clear conversation history from Redis
        session_history = get_session_history(request.session_id)
        session_history.clear()
        print(f"--- Cleared conversation history for session: {request.session_id} ---")

        # 2. Delete RAG documents from ChromaDB
        delete_documents_by_session_id(request.session_id)
        
        message = f"Successfully reset all data for session {request.session_id}."
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset session data: {e}")
    finally:
        end_time = time.time()
        processing_duration = end_time - start_time

    return ResetResponse(message=message, processing_duration=processing_duration)
