# backend/app/api/v1/endpoints/chat.py

import time
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.agents import agent_manager

router = APIRouter()

class ChatRequest(BaseModel):
    session_id: str
    message: str
    use_rag: bool = False
    use_web_search: bool = False

class ChatResponse(BaseModel):
    response: str
    processing_duration: float

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handles chat requests with integrated session history management."""
    start_time = time.time()
    
    try:
        # THE FIX IS HERE: The key must match 'input_messages_key' from the agent manager.
        # The value should be the raw string content of the message.
        input_data = {
            "messages": request.message, # <-- CRITICAL FIX: Changed "message" to "messages"
            "use_rag": request.use_rag,
            "use_web_search": request.use_web_search,
        }

        # The thread_id is used by the checkpointer to save state.
        config = {"configurable": {"session_id": request.session_id, "thread_id": request.session_id}}

        # Invoke the agent from the manager
        agent_with_history = await agent_manager.get_agent_with_history()
        response_state = await agent_with_history.ainvoke(input_data, config=config)
        
        # The final response is the last message in the state's message list
        response_content = response_state["messages"][-1].content

    except Exception as e:
        print(f"--- ERROR: Exception during chat execution: {e} ---")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An error occurred during chat execution.")

    finally:
        end_time = time.time()
        processing_duration = end_time - start_time

    return ChatResponse(response=response_content, processing_duration=processing_duration)