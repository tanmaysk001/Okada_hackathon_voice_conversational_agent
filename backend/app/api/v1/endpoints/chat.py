import time
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from app.agent.graph import create_agent_graph
from app.core.session import get_session_history

# Create the agent graph
agent_graph = create_agent_graph()

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
    """Manually manages history and calls the agent graph directly."""
    start_time = time.time()
    
    try:
        # 1. Get the session history object
        history = get_session_history(request.session_id)
        
        # 2. Load previous messages
        previous_messages = await history.aget_messages()
        
        # 3. Create the new user message
        new_user_message = HumanMessage(content=request.message)
        
        # 4. Construct the full message history
        all_messages = previous_messages + [new_user_message]

        # 5. Manually construct the state for the graph
        initial_state = {
            "messages": all_messages,
            "session_id": request.session_id,
            "use_rag": request.use_rag,
            "use_web_search": request.use_web_search,
            "context": ""  # Ensure context is initialized
        }

        # 6. Invoke the graph directly
        print(f"--- DEBUG: Invoking graph with state: {initial_state} ---")
        response_state = await agent_graph.ainvoke(initial_state)
        print(f"--- DEBUG: Graph returned state: {response_state} ---")
        
        # 7. Extract the AI's response
        ai_response_message = response_state["messages"][-1]
        response_content = ai_response_message.content

        # 8. Save the new user message and AI response to history
        await history.aadd_messages([new_user_message, ai_response_message])

    except Exception as e:
        print(f"--- ERROR: Exception during chat execution: {e} ---")
        print(traceback.format_exc()) # Print the full stack trace
        raise HTTPException(status_code=500, detail="An error occurred during chat execution.")

    finally:
        end_time = time.time()
        processing_duration = end_time - start_time

    return ChatResponse(response=response_content, processing_duration=processing_duration)
