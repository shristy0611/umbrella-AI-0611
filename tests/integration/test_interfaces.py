import pytest
import httpx
import os
import json
import base64
from datetime import datetime
from typing import Dict

# Service URLs
PDF_SERVICE_URL = os.getenv("PDF_SERVICE_URL", "http://localhost:8001")
SENTIMENT_SERVICE_URL = os.getenv("SENTIMENT_SERVICE_URL", "http://localhost:8002")
CHATBOT_SERVICE_URL = os.getenv("CHATBOT_SERVICE_URL", "http://localhost:8003")
SCRAPER_SERVICE_URL = os.getenv("SCRAPER_SERVICE_URL", "http://localhost:8004")
VECTOR_DB_URL = os.getenv("VECTOR_DB_URL", "http://localhost:8005")

# Test data
TEST_PDF_PATH = "tests/data/test.pdf"
TEST_TEXT = "This is a great test message! I'm very happy with the results."
TEST_URL = "http://example.com"

@pytest.fixture
def headers():
    return {
        "X-Correlation-ID": "test-correlation-id",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

@pytest.mark.asyncio
async def test_health_endpoints(headers):
    """Test health check endpoints for all services."""
    services = {
        "pdf": PDF_SERVICE_URL,
        "sentiment": SENTIMENT_SERVICE_URL,
        "chatbot": CHATBOT_SERVICE_URL,
        "scraper": SCRAPER_SERVICE_URL,
        "vector_db": VECTOR_DB_URL
    }
    
    async with httpx.AsyncClient() as client:
        for service_name, url in services.items():
            response = await client.get(f"{url}/health", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["healthy", "unhealthy"]
            assert "service" in data

@pytest.mark.asyncio
async def test_pdf_extraction_interface(headers):
    """Test PDF extraction service interface."""
    # Create a dummy PDF file if it doesn't exist
    if not os.path.exists(TEST_PDF_PATH):
        with open(TEST_PDF_PATH, "wb") as f:
            f.write(b"%PDF-1.7\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n")
    
    async with httpx.AsyncClient() as client:
        with open(TEST_PDF_PATH, "rb") as pdf:
            files = {"file": ("test.pdf", pdf, "application/pdf")}
            response = await client.post(
                f"{PDF_SERVICE_URL}/extract",
                headers=headers,
                files=files
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "text" in data
            assert "pages" in data
            assert "metadata" in data

@pytest.mark.asyncio
async def test_sentiment_analysis_interface(headers):
    """Test sentiment analysis service interface."""
    request_data = {
        "text": TEST_TEXT,
        "metadata": {
            "source": "test",
            "context": "integration_test"
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SENTIMENT_SERVICE_URL}/analyze",
            headers=headers,
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "sentiment" in data
        assert "score" in data
        assert data["sentiment"] in ["positive", "negative", "neutral"]
        assert 0 <= data["score"] <= 1

@pytest.mark.asyncio
async def test_chatbot_interface(headers):
    """Test chatbot service interface."""
    session_id = "test-session"
    
    # Test chat endpoint
    request_data = {
        "session_id": session_id,
        "message": "Hello, how are you?",
        "context": {
            "previous_messages": [],
            "metadata": {
                "source": "test",
                "user_id": "test-user"
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        # Test chat
        response = await client.post(
            f"{CHATBOT_SERVICE_URL}/chat",
            headers=headers,
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "confidence" in data
        assert "metadata" in data
        
        # Test history
        response = await client.get(
            f"{CHATBOT_SERVICE_URL}/history/{session_id}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        
        # Test clear history
        response = await client.delete(
            f"{CHATBOT_SERVICE_URL}/history/{session_id}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

@pytest.mark.asyncio
async def test_scraper_interface(headers):
    """Test RAG scraper service interface."""
    request_data = {
        "url": TEST_URL,
        "max_depth": 1,
        "max_pages": 2,
        "selectors": ["h1", "p"],
        "exclude_patterns": ["*blog*", "*archive*"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SCRAPER_SERVICE_URL}/scrape",
            headers=headers,
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "metadata" in data
        assert "discovered_urls" in data

@pytest.mark.asyncio
async def test_vector_db_interface(headers):
    """Test vector database service interface."""
    # Test adding vector
    add_request = {
        "text": "Test document for vector storage",
        "metadata": {
            "source": "test",
            "type": "document",
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    async with httpx.AsyncClient() as client:
        # Add vector
        response = await client.post(
            f"{VECTOR_DB_URL}/vectors/add",
            headers=headers,
            json=add_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "vector_id" in data
        
        # Search vectors
        search_request = {
            "query": "Test document",
            "k": 1,
            "filter": {
                "source": "test",
                "type": "document"
            }
        }
        
        response = await client.post(
            f"{VECTOR_DB_URL}/vectors/search",
            headers=headers,
            json=search_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "results" in data
        assert len(data["results"]) > 0

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 