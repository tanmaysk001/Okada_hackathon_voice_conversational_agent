import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
from app.core.config import settings

class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

db_manager = MongoDB()

async def connect_to_mongo():
    print("Connecting to MongoDB...")
    db_manager.client = AsyncIOMotorClient(settings.MONGO_URI)
    db_manager.db = db_manager.client[settings.MONGO_DB_NAME]
    print("Successfully connected to MongoDB.")

async def close_mongo_connection():
    print("Closing MongoDB connection...")
    if db_manager.client:
        # Run the synchronous close method in a separate thread
        await asyncio.to_thread(db_manager.client.close)
    print("MongoDB connection closed.")

def get_database() -> AsyncIOMotorDatabase:
    """
    Returns the database instance.
    """
    if db_manager.db is None:
        raise RuntimeError("Database connection not established. Ensure connect_to_mongo() has been awaited.")
    return db_manager.db