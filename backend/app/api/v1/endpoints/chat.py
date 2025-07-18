# backend/app/api/v1/endpoints/chat.py

import time
import asyncio
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.agents import agent_manager
from langchain_core.messages import HumanMessage
from app.services import persistent_history_service


router = APIRouter()

class ChatRequest(BaseModel):
    session_id: str  # This is the unique ID for the conversation thread
    user_email: str # The user's email address
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
            "messages": [HumanMessage(content=request.message)],
            "use_rag": request.use_rag,
            "use_web_search": request.use_web_search,
            "session_id": request.session_id
        }

        # The thread_id is used by the checkpointer to save state.
        # The session_id in here is redundant now but harmless.
        config = {
            "configurable": {
                "thread_id": request.session_id,
                "session_id": request.session_id
            },
            "recursion_limit": 50,
        }

        # Invoke the agent from the manager
        agent_with_history = agent_manager.get_agent_with_history()
        response_state = await agent_with_history.ainvoke(input_data, config=config)
        
        # The final response is the last message in the state's message list
        response_content = response_state["messages"][-1].content

        asyncio.create_task(
            persistent_history_service.add_message_to_history(
                user_email=request.user_email,
                session_id=request.session_id,
                user_message=request.message,
                assistant_message=response_content
            )
        )

    except Exception as e:
        print(f"--- ERROR: Exception during chat execution: {e} ---")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An error occurred during chat execution.")

    finally:
        end_time = time.time()
        processing_duration = end_time - start_time

    return ChatResponse(response=response_content, processing_duration=processing_duration)