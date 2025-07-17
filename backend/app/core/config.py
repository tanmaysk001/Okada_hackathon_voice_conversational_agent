from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # From Project 2
    GOOGLE_API_KEY: str
    TAVILY_API_KEY: str
    REDIS_URL: str = "redis://localhost:6379"

    # From Project 1
    MONGO_URI: str
    MONGO_DB_NAME: str
    GOOGLE_CALENDAR_CREDENTIALS_PATH: str
    CHROMA_PERSIST_DIRECTORY: str = "./user_chroma_db"
    CHROMA_HOST: Optional[str] = None
    CHROMA_PORT: Optional[int] = None
    CHROMA_COLLECTION_PREFIX: str = "okada_user_"

    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

settings = Settings()