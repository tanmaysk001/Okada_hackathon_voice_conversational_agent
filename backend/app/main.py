# In: apps/backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import chat, upload, live_chat, history, management, audio 

# Create the FastAPI app instance
app = FastAPI(
    title="Intelligent Chatbot API",
    version="1.0.0",
)

# --- ADD THIS CORS MIDDLEWARE SECTION ---
# List of origins that are allowed to make requests to your API
# The default Vite dev server runs on 5173
origins = [
    "http://localhost:5173",
    "http://localhost:3000", 
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True, # Allows cookies to be included in requests
    allow_methods=["*"],    # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],    # Allows all headers
)
# -----------------------------------------

# Include your API routers
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(upload.router, prefix="/api/v1", tags=["RAG Document Upload"])
app.include_router(live_chat.router, prefix="/ws/v1", tags=["Live Chat"])
app.include_router(history.router, prefix="/api/v1/history", tags=["History"])
app.include_router(management.router, prefix="/api/v1", tags=["Management"])
app.include_router(audio.router, prefix="/api/v1", tags=["Audio"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Intelligent Chatbot API!"}