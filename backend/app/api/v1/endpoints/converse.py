# backend/app/api/v1/endpoints/converse.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.agents import agent_manager

router = APIRouter()

class ConverseRequest(BaseModel):
    session_id: str
    message: str
    use_rag: bool = False
    use_web_search: bool = False

class ConverseResponse(BaseModel):
    response: str

@router.post("/converse", response_model=ConverseResponse)
async def converse(request: ConverseRequest):
    """Handles both text and voice conversations with persistent memory."""
    config = {"configurable": {"session_id": request.session_id, "thread_id": request.session_id}}
    
    # THE FIX IS HERE: Ensure the input key matches the agent's expected key.
    input_data = {
        "messages": request.message, # <-- CRITICAL FIX: Changed "message" to "messages"
        "use_rag": request.use_rag,
        "use_web_search": request.use_web_search,
    }
    try:
        # Use the agent from the manager
        agent_with_history = await agent_manager.get_agent_with_history()
        response = await agent_with_history.ainvoke(input_data, config=config)
        return ConverseResponse(response=response["messages"][-1].content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))