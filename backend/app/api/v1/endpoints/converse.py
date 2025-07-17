from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.main import agent_graph

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
    config = {"configurable": {"session_id": request.session_id}}
    input_data = {
        "message": request.message,
        "use_rag": request.use_rag,
        "use_web_search": request.use_web_search,
    }
    try:
        response = await agent_graph.ainvoke(input_data, config=config)
        return ConverseResponse(response=response["messages"][-1].content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
