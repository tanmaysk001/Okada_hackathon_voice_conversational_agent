"""
User management API endpoints for the Okada RAG Voice conversational agent.

This module provides endpoints for:
1. Creating or updating user profiles
2. Retrieving user information
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, Optional

from app.services import crm_service
from app.models.crm_models import User

# Create router for user management endpoints
router = APIRouter(tags=["User Management"])


@router.post("/user", response_model=User)
async def handle_create_or_update_user(user_data: dict):
    """
    Create a new user or update an existing user in the CRM system.
    
    Required fields:
    - email: User's email address (used as unique identifier)
    
    Optional fields:
    - full_name: User's full name
    - company_name: User's company name
    """
    try:
        email = user_data.get("email")
        full_name = user_data.get("full_name")
        company_name = user_data.get("company_name")
        phone_number = user_data.get("phone_number") # Add this
        password = user_data.get("password") # Add this

        # NOTE: In a real app, you MUST hash the password here.
        # For the hackathon demo, we'll store it directly for speed.
        hashed_password = f"hashed_{password}_demo" if password else None

        if not email:
            raise HTTPException(status_code=400, detail="Email is required.")
            
        user = await crm_service.create_or_update_user(
            full_name=full_name or "Unknown User", # Provide a default if name is missing on update
            email=email,
            company_name=company_name,
            phone_number=phone_number, # Add this
            hashed_password=hashed_password # Add this
        )
        return user
    except Exception as e:
        print(f"Error in handle_create_or_update_user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create or update user: {str(e)}")


@router.get("/user", response_model=User)
async def handle_get_user(email: str):
    """
    Get a user's information from the CRM system by email address.
    
    Args:
        email: User's email address
    
    Returns:
        User object if found
        
    Raises:
        404: If user not found
        500: If database error occurs
    """
    try:
        # First, try to fetch the user from the database
        user = await crm_service.get_user_by_email(email)
    except Exception as e:
        # If there's a database connection error, it's a 500
        print(f"Database error in handle_get_user: {e}")
        raise HTTPException(status_code=500, detail="A database error occurred.")

    # If the database call was successful but no user was returned...
    if not user:
        # ...then it's a 404 Not Found, which is what the frontend expects.
        raise HTTPException(status_code=404, detail="User not found.")

    # If a user was found, return their data
    return user
