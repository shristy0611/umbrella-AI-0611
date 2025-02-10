import pytest
from fastapi.testclient import TestClient
from src.main import app, TaskGraph, SubTask

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "services" in response.json()
    services = response.json()["services"]
    assert all(service in services for service in [
        "pdf_extraction",
        "sentiment",
        "chatbot",
        "rag_scraper",
        "vector_db"
    ])

def test_process_invalid_task():
    request_data = {
        "task_type": "invalid_task",
        "content": {},
        "context": {}
    }
    response = client.post("/process", json=request_data)
    assert response.status_code == 400
    assert "Unknown task type" in response.json()["detail"]

def test_process_document_analysis():
    request_data = {
        "task_type": "document_analysis",
        "content": {
            "file": "test.pdf",
            "source": "test"
        },
        "context": {}
    }
    response = client.post("/process", json=request_data)
    assert response.status_code == 200
    assert "status" in response.json()
    assert "result" in response.json()
    result = response.json()["result"]
    assert "extract_pdf" in result
    assert "analyze_sentiment" in result
    assert "store_vector" in result

def test_process_chat_with_context():
    request_data = {
        "task_type": "chat_with_context",
        "content": {
            "message": "Test message",
            "session_id": "test_session",
            "max_results": 3
        },
        "context": {}
    }
    response = client.post("/process", json=request_data)
    assert response.status_code == 200
    result = response.json()["result"]
    assert "search_context" in result
    assert "generate_response" in result

def test_process_web_research():
    request_data = {
        "task_type": "web_research",
        "content": {
            "url": "http://example.com",
            "max_depth": 1,
            "selectors": ["h1", "p"]
        },
        "context": {}
    }
    response = client.post("/process", json=request_data)
    assert response.status_code == 200
    result = response.json()["result"]
    assert "scrape_content" in result
    assert "store_scraped" in result
    assert "analyze_content" in result

@pytest.mark.asyncio
async def test_task_graph_execution():
    # Create a test task graph
    graph = TaskGraph()
    
    # Add tasks with dependencies
    graph.add_task("task1", SubTask(
        service="pdf_extraction",
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

@pytest.mark.asyncio
async def test_task_graph_parallel_execution():
    graph = TaskGraph()
    
    # Add independent tasks that can run in parallel
    graph.add_task("task1", SubTask(
        service="pdf_extraction",
        action="extract",
        data={"file": "test1.pdf"},
        priority=1
    ))
    
    graph.add_task("task2", SubTask(
        service="sentiment",
        action="analyze",
        data={"text": "test text"},
        priority=1  # Same priority, can run in parallel
    ))
    
    # Add dependent task
    graph.add_task("task3", SubTask(
        service="vector_db",
        action="add",
        data={
            "text": "$result.task1.text",
            "sentiment": "$result.task2.sentiment"
        },
        priority=2,
        dependencies=["task1", "task2"]
    ))
    
    results = await graph.execute("test-correlation-id")
    
    assert len(results) == 3
    assert all(task in results for task in ["task1", "task2", "task3"])

def test_correlation_id_propagation():
    request_data = {
        "task_type": "sentiment_analysis",
        "content": {
            "text": "Test message"
        },
        "context": {}
    }
    response = client.post("/process", json=request_data)
    assert response.status_code == 200
    assert "correlation_id" in response.json()["metadata"]
    assert response.headers.get("X-Correlation-ID") is not None 