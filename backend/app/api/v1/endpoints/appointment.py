from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any

from app.services.appointment_workflow import appointment_workflow_manager
from app.models.crm_models import WorkflowResponse

router = APIRouter()

@router.post("/start", response_model=WorkflowResponse)
async def start_appointment(payload: Dict[str, Any] = Body(...)):
    user_id = payload.get("user_id")
    message = payload.get("message")
    if not user_id or not message:
        raise HTTPException(status_code=400, detail="'user_id' and 'message' are required.")
    
    try:
        response = await appointment_workflow_manager.start_appointment_booking(user_id, message)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/continue", response_model=WorkflowResponse)
async def continue_appointment(session_id: str, payload: Dict[str, Any] = Body(...)):
    user_response = payload.get("user_response")
    if not user_response:
        raise HTTPException(status_code=400, detail="'user_response' is required.")
    
    try:
        response = await appointment_workflow_manager.process_user_response(session_id, user_response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/confirm", response_model=WorkflowResponse)
async def confirm_appointment(session_id: str):
    try:
        response = await appointment_workflow_manager.confirm_appointment(session_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/cancel", response_model=WorkflowResponse)
async def cancel_appointment(session_id: str):
    try:
        response = await appointment_workflow_manager.cancel_appointment(session_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
