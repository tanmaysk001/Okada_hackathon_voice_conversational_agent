import time
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from app.agent.graph import create_agent_graph
from app.core.session import get_session_history

# Create the agent graph


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
        # The input to the agent now only requires the message and other specific keys,
        # not the entire history, which is managed by RunnableWithMessageHistory.
        input_data = {
            "message": request.message,
            "session_id": request.session_id,
            "use_rag": request.use_rag,
            "use_web_search": request.use_web_search,
        }

        # Define the session configuration for the agent
        config = {"configurable": {"session_id": request.session_id}}

        # Create the agent graph and wrap it with message history
        # Create the agent graph
        agent_executor = create_agent_graph()

        # Create the agent with message history, passing the synchronous factory function
        agent_with_history = RunnableWithMessageHistory(
            agent_executor,
            get_session_history,  # Pass the synchronous factory directly
            input_messages_key="message",
            history_messages_key="messages",
        )

        # Invoke the agent with the input data and configuration
        print(f"--- DEBUG: Invoking agent with history with input: {input_data} and config: {config} ---")
        response_state = await agent_with_history.ainvoke(input_data, config=config)
        print(f"--- DEBUG: Agent returned state: {response_state} ---")
        
        # Extract the AI's response from the final state
        # The response is expected in the 'messages' list, as the last message
        response_content = response_state["messages"][-1].content

    except Exception as e:
        print(f"--- ERROR: Exception during chat execution: {e} ---")
        print(traceback.format_exc()) # Print the full stack trace
        raise HTTPException(status_code=500, detail="An error occurred during chat execution.")

    finally:
        end_time = time.time()
        processing_duration = end_time - start_time

    return ChatResponse(response=response_content, processing_duration=processing_duration)
