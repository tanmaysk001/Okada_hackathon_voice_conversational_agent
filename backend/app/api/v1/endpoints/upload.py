import os
import uuid
import time
import redis
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.services import document_parser, vector_store
from app.core.session_manager import set_session_file_info
from app.core.config import settings

# Initialize Redis client
redis_client = redis.from_url(settings.REDIS_URL)

router = APIRouter()

TEMP_UPLOADS_DIR = "temp_uploads"
os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)

class UploadResponse(BaseModel):
    session_id: str
    message: str
    file_path: str
    processing_duration: float

@router.post("/upload_rag_docs", response_model=UploadResponse)
async def upload_rag_docs(session_id: str = Form(...), file: UploadFile = File(...)):
    """
    Handles the upload of various file types (PDF, TXT, CSV, JSON, DOCX) for 
    the Retrieval Augmented Generation (RAG) system.

    The endpoint performs the following steps:
    1.  Validates the file type.
    2.  Saves the uploaded file to a temporary directory.
    3.  Invokes the `document_parser` service to process the file into a 
        standardized format (list of LangChain `Document` objects).
    4.  Adds the processed documents to the ChromaDB vector store, associating 
        them with the provided `session_id`.
    5.  Records that a RAG file has been processed for this session.
    6.  Returns a confirmation message along with the processing time.
    """
    start_time = time.time()
    
    file_extension = file.filename.split(".")[-1].lower()
    supported_types = ['pdf', 'txt', 'md', 'csv', 'json', 'docx', 'doc']

    if file_extension not in supported_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: '{file_extension}'. Supported types are: {supported_types}"
        )

    try:
        # 1. Save the file to a temporary location
        file_path = os.path.join(TEMP_UPLOADS_DIR, f"{uuid.uuid4()}_{file.filename}")
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # 2. Parse the file into LangChain Documents
        # This now robustly handles CSV and JSON as well
        documents = document_parser.parse_file(file_path, file_extension)

        # 3. Add the processed documents to the vector store
        vector_store.add_documents_to_store(documents, session_id)

        # 4. Mark that a RAG file is active for this session
        set_session_file_info(session_id, file_type='rag', file_path=file_path)

        # 5. Store the filename in Redis for this session
        try:
            redis_client.rpush(f"uploaded_files:{session_id}", file.filename)
        except Exception as redis_e:
            # Log the Redis error but don't fail the whole upload
            print(f"Could not save filename to Redis: {redis_e}")

        message = f"Successfully processed and indexed '{file.filename}' for RAG."

    except Exception as e:
        # Log the exception for debugging
        print(f"Error during file upload processing: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while processing the file: {e}")

    finally:
        end_time = time.time()
        processing_duration = end_time - start_time

    return UploadResponse(
        session_id=session_id,
        message=message,
        file_path=file_path,
        processing_duration=processing_duration
    )

@router.get("/uploads/{session_id}", response_model=List[str])
async def get_uploaded_files(session_id: str):
    """
    Retrieves the list of uploaded file names for a given session ID from Redis.
    """
    try:
        # The key for the list of uploaded files
        key = f"uploaded_files:{session_id}"
        # Retrieve all items from the list
        file_names_bytes = redis_client.lrange(key, 0, -1)
        # Decode from bytes to string
        file_names = [name.decode('utf-8') for name in file_names_bytes]
        return file_names
    except Exception as e:
        print(f"Error retrieving uploaded files from Redis: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve file list from Redis.")