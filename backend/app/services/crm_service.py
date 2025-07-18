import re
from typing import Optional, List
from app.services.database_service import get_database
from app.models.crm_models import User, Company
from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def get_domain_from_email(email: str) -> Optional[str]:
    """Extracts the domain from an email address."""
    match = re.search(r"@([\w.-]+)", email)
    return match.group(1) if match else None

async def get_or_create_company(domain: str, company_name: Optional[str] = None) -> Company:
    """
    Retrieves a company by its domain. If it doesn't exist, a new company is created.
    """
    db = get_database()
    company_collection: AsyncIOMotorCollection = db["companies"]
    
    company_data = await company_collection.find_one({"domain": re.compile(f"^{re.escape(domain)}$", re.IGNORECASE)})
    
    if company_data:
        return Company(**company_data)
    else:
        name_to_use = company_name if company_name else domain
        new_company = Company(name=name_to_use, domain=domain)
        
        company_dict = new_company.model_dump(by_alias=True, exclude_none=True)

        result = await company_collection.insert_one(company_dict)
        new_company.id = result.inserted_id
        return new_company

async def get_user_by_email(email: str) -> Optional[User]:
    """
    Retrieves a user by their email address.
    """
    db = get_database()
    user_collection: AsyncIOMotorCollection = db["users"]
    user_data = await user_collection.find_one({"email": email})
    return User(**user_data) if user_data else None


async def create_or_update_user(
    email: str,
    full_name: Optional[str] = None,
    company_name: Optional[str] = None,
    preferences: Optional[dict] = None,
    recommendation_preferences: Optional[dict] = None
) -> User:
    """
    Creates a new user or updates an existing one.
    Handles partial updates and merges preferences.
    """
    db = get_database()
    user_collection: AsyncIOMotorCollection = db["users"]
    
    existing_user_data = await user_collection.find_one({"email": email})

    if existing_user_data:
        update_data = {}
        if full_name:
            update_data["full_name"] = full_name
        
        if company_name:
            domain = get_domain_from_email(email)
            if domain:
                company = await get_or_create_company(domain, company_name)
                update_data["company_id"] = company.id
        
        if preferences:
            for key, value in preferences.items():
                update_data[f"preferences.{key}"] = value
        
        if recommendation_preferences:
            for key, value in recommendation_preferences.items():
                update_data[f"recommendation_preferences.{key}"] = value

        if update_data:
            await user_collection.update_one({"_id": existing_user_data["_id"]}, {"$set": update_data})
        
        updated_user_data = await user_collection.find_one({"_id": existing_user_data["_id"]})
        if not updated_user_data:
            raise ValueError(f"User with ID {existing_user_data['_id']} could not be found after update.")
        return User(**updated_user_data)

    else:
        if not full_name:
            raise ValueError("Full name is required for new user creation.")

        domain = get_domain_from_email(email)
        company_id = None
        if domain:
            company = await get_or_create_company(domain, company_name)
            company_id = company.id

        new_user = User(
            full_name=full_name,
            email=email,
            company_id=company_id,
            hashed_password=hashed_password, # Add this
            preferences=preferences or {},
            recommendation_preferences=recommendation_preferences or {}
        )
        user_dict = new_user.model_dump(by_alias=True, exclude_none=True)
        result = await user_collection.insert_one(user_dict)
        new_user.id = result.inserted_id
        return new_user


async def delete_user_by_email(email: str) -> bool:
    """
    Deletes a single user from the database based on their email.
    Returns True if a user was deleted, False otherwise.
    """
    db = get_database()
    user_collection: AsyncIOMotorCollection = db["users"]
    delete_result = await user_collection.delete_one({"email": email})
    return delete_result.deleted_count > 0

async def add_appointment_to_user(user_email: str, session_id: str, appointment_data: dict) -> bool:
    """
    Add an appointment to a user's history.
    """
    try:
        db = get_database()
        user_collection = db["users"]
        
        result = await user_collection.update_one(
            {"email": user_email},
            {
                "$push": {"appointment_history": session_id},
                "$set": {"updated_at": datetime.now()}
            }
        )
        
        appointment_collection = db["user_appointments"]
        await appointment_collection.insert_one({
            "user_email": user_email,
            "session_id": session_id,
            "appointment_data": appointment_data,
            "created_at": datetime.now()
        })
        
        return result.modified_count > 0
        
    except Exception as e:
        logger.error(f"Error adding appointment to user {user_email}: {e}")
        return False

async def get_user_appointments(user_email: str) -> List[dict]:
    """
    Get all appointments for a user.
    """
    try:
        db = get_database()
        appointment_collection = db["user_appointments"]
        
        appointments = []
        async for appointment in appointment_collection.find(
            {"user_email": user_email}
        ).sort("created_at", -1):
            appointments.append(appointment)
        
        return appointments
        
    except Exception as e:
        logger.error(f"Error getting appointments for user {user_email}: {e}")
        return []

async def update_appointment_preferences(user_email: str, preferences: dict) -> bool:
    """
    Update a user's appointment preferences.
    """
    try:
        db = get_database()
        user_collection = db["users"]
        
        result = await user_collection.update_one(
            {"email": user_email},
            {
                "$set": {
                    "appointment_preferences": preferences,
                    "updated_at": datetime.now()
                }
            }
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        logger.error(f"Error updating appointment preferences for user {user_email}: {e}")
        return False