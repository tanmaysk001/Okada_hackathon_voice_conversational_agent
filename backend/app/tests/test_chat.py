import pytest
from fastapi.testclient import TestClient
from app.main import app # Assuming your FastAPI app instance is in app/main.py

client = TestClient(app)

def test_chat_endpoint_success():
    """Tests the /api/v1/chat endpoint for a successful response."""
    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "test-session-123",
            "message": "Hello, what is LangGraph?",
            "use_rag": False,
            "use_web_search": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "processing_duration" in data
    assert isinstance(data["response"], str)
    assert data["response"] != ""

def test_chat_endpoint_rag():
    """Tests the RAG functionality of the chat endpoint."""
    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "test-rag-456",
            "message": "Tell me about the project architecture.",
            "use_rag": True,
            "use_web_search": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data

# To run these tests, navigate to your `backend` directory in the terminal
# and simply run the command: pytest
