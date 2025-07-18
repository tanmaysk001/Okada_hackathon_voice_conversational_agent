# backend/app/services/persistent_history_service.py

from app.services.database_service import get_database
from app.models.crm_models import ConversationHistory, ChatMessage
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import List
import datetime as dt
import logging

async def get_history_collection() -> AsyncIOMotorCollection:
    """Returns the conversation_history collection from the database."""
    db = get_database()
    return db["conversation_history"]



async def get_conversation_history(user_email: str, session_id: str) -> List[dict]:
    """
    Retrieves the conversation history for a specific session of a user from MongoDB.
    """
    history_collection = await get_history_collection()
    conversation_data = await history_collection.find_one(
        {"user_email": user_email, "session_id": session_id}
    )
    if conversation_data and "messages" in conversation_data:
        history_obj = ConversationHistory(**conversation_data)
        return [msg.model_dump() for msg in history_obj.messages]
    return []

async def add_message_to_history(user_email: str, session_id: str, user_message: str, assistant_message: str):
    logging.info(f"Attempting to add message for user='{user_email}' session='{session_id}'")
    try:
        history_collection = await get_history_collection()
        
        # Standardize on the Pydantic model for consistency
        new_messages_to_add = [
            ChatMessage(role="user", content=user_message),
            ChatMessage(role="assistant", content=assistant_message),
        ]
        
        # The query to find the existing conversation document
        query = {"user_email": user_email, "session_id": session_id}

        # Use find_one_and_update with upsert=True. This is atomic and safer.
        # It finds the document and pushes the new messages.
        # If it doesn't find a document, it creates a new one with all the fields.
        result = await history_collection.find_one_and_update(
            query,
            {
                "$push": {"messages": {"$each": [msg.model_dump() for msg in new_messages_to_add]}},
                "$set": {"updated_at": dt.datetime.utcnow()},
                "$setOnInsert": {
                    "user_email": user_email,
                    "session_id": session_id,
                    "created_at": dt.datetime.utcnow(),
                    "tags": []
                }
            },
            upsert=True, # This is the key: creates the document if it doesn't exist
            return_document=True
        )

        if result:
            logging.info(f"Successfully updated/created history for user='{user_email}' session='{session_id}'")
        else:
            logging.error(f"Failed to update or insert history for user='{user_email}' session='{session_id}'")

    except Exception as e:
            logging.info(f"Successfully created new history document with ID: {result.inserted_id} for user='{user_email}' session='{session_id}'")
    except Exception as e:
        logging.error(f"Failed to add message to history for user='{user_email}' session='{session_id}': {e}", exc_info=True)