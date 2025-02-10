import pytest
import httpx
import asyncio
import os
from typing import Dict

# Service URLs from environment variables with localhost defaults
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")
PDF_SERVICE_URL = os.getenv("PDF_SERVICE_URL", "http://localhost:8001")
SENTIMENT_SERVICE_URL = os.getenv("SENTIMENT_SERVICE_URL", "http://localhost:8002")
CHATBOT_SERVICE_URL = os.getenv("CHATBOT_SERVICE_URL", "http://localhost:8003")
SCRAPER_SERVICE_URL = os.getenv("SCRAPER_SERVICE_URL", "http://localhost:8004")
VECTOR_DB_URL = os.getenv("VECTOR_DB_URL", "http://localhost:8005")

@pytest.mark.asyncio
async def test_service_health():
    """Test that all services are healthy and responding."""
    services = {
        "orchestrator": ORCHESTRATOR_URL,
        "pdf_extraction": PDF_SERVICE_URL,
        "sentiment": SENTIMENT_SERVICE_URL,
        "chatbot": CHATBOT_SERVICE_URL,
        "rag_scraper": SCRAPER_SERVICE_URL,
        "vector_db": VECTOR_DB_URL
    }
    
    async with httpx.AsyncClient() as client:
        for service_name, url in services.items():
            response = await client.get(f"{url}/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            print(f"{service_name} health check: {data}")

@pytest.mark.asyncio
async def test_orchestrator_task_routing():
    """Test that orchestrator can route tasks to appropriate services."""
    async with httpx.AsyncClient() as client:
        # Test sentiment analysis task
        sentiment_task = {
            "task_type": "sentiment",
            "data": {
                "text": "This is a test message",
                "metadata": {"source": "integration_test"}
            },
            "context": {"test": True}
        }
        response = await client.post(f"{ORCHESTRATOR_URL}/process", json=sentiment_task)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert "result" in result

@pytest.mark.asyncio
async def test_vector_db_operations():
    """Test vector database operations."""
    async with httpx.AsyncClient() as client:
        # Test adding vector
        add_request = {
            "text": "Test document for vector storage",
            "metadata": {"source": "integration_test"}
        }
        response = await client.post(f"{VECTOR_DB_URL}/vectors/add", json=add_request)
        assert response.status_code == 200
        
        # Test searching vectors
        search_request = {
            "query": "Test document",
            "k": 1
        }
        response = await client.post(f"{VECTOR_DB_URL}/vectors/search", json=search_request)
        assert response.status_code == 200
        result = response.json()
        assert "results" in result

@pytest.mark.asyncio
async def test_chatbot_conversation():
    """Test chatbot conversation flow."""
    async with httpx.AsyncClient() as client:
        chat_request = {
            "session_id": "test_session",
            "message": "Hello, how are you?",
            "context": {"test": True}
        }
        response = await client.post(f"{CHATBOT_SERVICE_URL}/chat", json=chat_request)
        assert response.status_code == 200
        result = response.json()
        assert "response" in result
        assert "confidence" in result
        
        # Test conversation history
        history_response = await client.get(f"{CHATBOT_SERVICE_URL}/history/test_session")
        assert history_response.status_code == 200
        history = history_response.json()
        assert "history" in history

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 