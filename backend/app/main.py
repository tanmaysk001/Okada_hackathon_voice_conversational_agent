import contextlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import upload, history, management, converse, audio, live_chat
from app.api.v1.endpoints.health import health_router
from app.api.v1.endpoints import user_management, appointment
from app.core.config import settings
from app.services.database_service import connect_to_mongo, close_mongo_connection

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    await connect_to_mongo()
    print("MongoDB connection established")
    
    yield
    
    # On shutdown
    await close_mongo_connection()
    print("MongoDB connection closed")

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Okada RAG Voice API",
    version="1.0.0",
    description="API for the Okada RAG Voice project, providing endpoints for chat, audio, and document management.",
    lifespan=lifespan
)

# --- CORS Middleware ---
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- API Routers ---
app.include_router(converse.router, prefix="/api/v1", tags=["Converse"])
app.include_router(upload.router, prefix="/api/v1", tags=["RAG Document Upload"])
app.include_router(history.router, prefix="/api/v1/history", tags=["History"])
app.include_router(management.router, prefix="/api/v1", tags=["Management"])
app.include_router(audio.router, prefix="/api/v1/audio", tags=["Audio"])
app.include_router(live_chat.router, prefix="/api/v1", tags=["Live Chat"])
app.include_router(health_router, prefix="/api/v1", tags=["Health Monitoring"])
app.include_router(user_management.router, prefix="/api/v1/users", tags=["User Management"])
app.include_router(appointment.router, prefix="/api/v1/appointment", tags=["Appointment Booking"])

# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
    """A simple endpoint to confirm the API is running."""
    return {"message": "Welcome to the Okada RAG Voice API!"}
