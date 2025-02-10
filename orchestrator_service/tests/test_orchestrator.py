import pytest
import httpx
from fastapi.testclient import TestClient
from src.main import app, TaskRequest, TaskGraph, SubTask

client = TestClient(app)

@pytest.fixture
def mock_service_responses(monkeypatch):
    """Mock responses for dependent services."""
    async def mock_post(*args, **kwargs):
        url = str(args[0])  # Convert URL to string for comparison
        response = httpx.Response(200, json={"status": "success"})
        
        if "pdf" in url and "extract" in url:
            response = httpx.Response(200, json={
                "text": "Sample PDF content",
                "pages": 1,
                "metadata": {"filename": "test.pdf"}
            })
        elif "sentiment" in url and "analyze" in url:
            response = httpx.Response(200, json={
                "sentiment": "positive",
                "score": 0.8,
                "metadata": {"text_length": 100}
            })
        elif "vector_db" in url:
            if "add" in url:
                response = httpx.Response(200, json={
                    "status": "success",
                    "vector_id": "123",
                    "message": "Vector added successfully"
                })
            else:
                response = httpx.Response(200, json={
                    "status": "success",
                    "results": [
                        {"distance": 0.1, "index": 0, "metadata": {}}
                    ]
                })
        elif "chatbot" in url and "chat" in url:
            response = httpx.Response(200, json={
                "response": "Test response",
                "confidence": 0.9,
                "metadata": {"session_id": "test-session"}
            })
        elif "scraper" in url and "scrape" in url:
            response = httpx.Response(200, json={
                "content": "Scraped content",
                "metadata": {
                    "pages_scraped": 1,
                    "timestamp": "2024-03-14T12:00:00Z"
                },
                "discovered_urls": ["http://test.com/page2"]
            })
        
        # Set request instance for raise_for_status
        response._request = httpx.Request("POST", url)
        return response

    async def mock_get(*args, **kwargs):
        url = str(args[0])
        response = httpx.Response(200, json={"status": "healthy"})
        response._request = httpx.Request("GET", url)
        return response

    # Mock both the AsyncClient and regular client
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

def test_health_check(mock_service_responses):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert all(service in data["services"] for service in ["pdf", "sentiment", "chatbot", "scraper", "vector_db"])

def test_document_analysis_workflow(mock_service_responses):
    """Test the document analysis workflow."""
    request = TaskRequest(
        task_type="document_analysis",
        content={"file": "test.pdf"},
        context={"source": "test"}
    )
    
    response = client.post("/process", json=request.model_dump())
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert "extract_pdf" in data["result"]
    assert "analyze_sentiment" in data["result"]
    assert "store_vector" in data["result"]

def test_chat_with_context_workflow(mock_service_responses):
    """Test the chat with context workflow."""
    request = TaskRequest(
        task_type="chat_with_context",
        content={
            "session_id": "test-session",
            "message": "Hello",
            "max_results": 3
        }
    )
    
    response = client.post("/process", json=request.model_dump())
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert "search_context" in data["result"]
    assert "generate_response" in data["result"]

def test_web_research_workflow(mock_service_responses):
    """Test the web research workflow."""
    request = TaskRequest(
        task_type="web_research",
        content={
            "url": "http://test.com",
            "max_depth": 1,
            "max_pages": 5
        }
    )
    
    response = client.post("/process", json=request.model_dump())
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert "scrape_content" in data["result"]
    assert "store_scraped" in data["result"]
    assert "analyze_content" in data["result"]

def test_invalid_task_type(mock_service_responses):
    """Test handling of invalid task types."""
    request = TaskRequest(
        task_type="invalid_type",
        content={"data": "test"}
    )
    
    response = client.post("/process", json=request.model_dump())
    assert response.status_code == 400
    assert "Unknown task type" in response.json()["detail"]

@pytest.mark.asyncio
async def test_task_graph_execution(mock_service_responses):
    """Test TaskGraph execution with dependencies."""
    graph = TaskGraph()
    
    # Add tasks with dependencies
    graph.add_task("task1", SubTask(
        service="pdf",
        action="extract",
        data={"file": "test.pdf"},
        priority=1
    ))
    
    graph.add_task("task2", SubTask(
        service="sentiment",
        action="analyze",
        data={"text": "$result.task1.text"},
        priority=2,
        dependencies=["task1"]
    ))
    
    # Execute graph
    results = await graph.execute("test-correlation-id")
    
    assert len(results) == 2
    assert "task1" in results
    assert "task2" in results
    assert results["task1"]["text"] == "Sample PDF content"
    assert results["task2"]["sentiment"] == "positive"

def test_correlation_id_middleware(mock_service_responses):
    """Test correlation ID middleware."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers

def test_error_handling(mock_service_responses):
    """Test error handling in the orchestrator."""
    # Test with invalid service
    request = TaskRequest(
        task_type="test",
        content={"invalid": True}
    )
    
    response = client.post("/process", json=request.model_dump())
    assert response.status_code == 400
    assert "Unknown task type" in response.json()["detail"]

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 