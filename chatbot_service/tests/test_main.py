import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import os
from chatbot_service.src.main import app, chat_sessions
import uuid

# Create test client
client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_env():
    """Mock environment variables for testing"""
    with patch.dict(os.environ, {
        "GEMINI_API_KEY_CHAT": "test-key",
        "VECTOR_DB_URL": "http://vector_db:8005"
    }):
        yield

@pytest.fixture
def mock_gemini():
    """Mock Gemini API responses"""
    with patch('google.generativeai.GenerativeModel') as mock:
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = MagicMock(text="Test response")
        mock.return_value = mock_instance
        yield mock

def test_health_check(mock_gemini):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "chatbot"
    assert "dependencies" in response.json()

def test_chat_endpoint(mock_gemini):
    """Test chat endpoint"""
    request_data = {
        "session_id": "test-session",
        "message": "Hello, how are you?",
        "context": {"test": True}
    }
    response = client.post("/chat", json=request_data)
    assert response.status_code == 200
    assert "response" in response.json()
    assert "session_id" in response.json()
    assert "metadata" in response.json()

def test_end_session():
    """Test ending a chat session"""
    session_id = "test-session"
    response = client.delete(f"/chat/{session_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_chat_history():
    session_id = str(uuid.uuid4())
    # First send a message
    chat_data = {
        "session_id": session_id,
        "message": "Test message",
        "context": {}
    }
    client.post("/chat", json=chat_data)
    
    # Then get history
    response = client.get(f"/history/{session_id}")
    assert response.status_code == 200
    assert "history" in response.json()
    assert len(response.json()["history"]) > 0

def test_clear_history():
    session_id = str(uuid.uuid4())
    response = client.delete(f"/history/{session_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success" 