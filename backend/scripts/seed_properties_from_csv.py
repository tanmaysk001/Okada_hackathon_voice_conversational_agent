# backend/scripts/seed_properties_from_csv.py
import asyncio
import pandas as pd
from motor.motor_asyncio import AsyncIOMotorClient
import os
import sys
from datetime import datetime

# Add the project root to the Python path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

# The path to your CSV file, relative to the `backend` directory
CSV_PATH = 'data/HackathonInternalKnowledgeBase.csv'

def clean_data(df):
    """Cleans and prepares the DataFrame for MongoDB insertion."""
    # Rename columns for better readability
    df.rename(columns={
        'Property Address': 'address',
        'Size (SF)': 'sq_ft',
        'Monthly Rent': 'rent_usd_str' # Keep as string for now
    }, inplace=True)

    # Clean the rent string (remove $, commas) and convert to a numeric type
    df['rent_usd'] = df['rent_usd_str'].replace({'\$': '', ',': ''}, regex=True).astype(float)
    
    # Convert DataFrame to a list of dictionaries
    records = df.to_dict('records')
    
    # Add a placeholder description for LLM context
    for record in records:
        record['description'] = f"A commercial suite located at {record['address']} with a size of {record['sq_ft']} square feet."
        record['amenities'] = ["Commercial Space", "Prime Location"]
        record['available_date'] = datetime.now() # Placeholder
        
    return records

async def seed_data():
    """Connects to the database and seeds the properties collection from the CSV."""
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {CSV_PATH}")
        return

    print(f"Reading data from {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)
    
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    properties_collection = db["properties"]

    # Clear existing data to ensure a fresh import
    await properties_collection.delete_many({})
    print("Cleared existing properties collection.")

    # Clean the data and prepare for insertion
    property_records = clean_data(df)

    # Insert the new data
    result = await properties_collection.insert_many(property_records)
    print(f"Successfully inserted {len(result.inserted_ids)} properties into the database.")
    client.close()

if __name__ == "__main__":
    # This allows running the script directly from the `backend` directory
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='.env')
    asyncio.run(seed_data())