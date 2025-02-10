import os
import pytest
from unittest.mock import AsyncMock, patch
from orchestrator_service.src.task_graph import TaskGraph, TaskStatus
from orchestrator_service.src.task_decomposer import SubTask, ServiceType

@pytest.fixture(autouse=True)
def setup_env():
    """Set up required environment variables for tests."""
    os.environ["PDF_SERVICE_URL"] = "http://pdf-service:8000"
    os.environ["SENTIMENT_SERVICE_URL"] = "http://sentiment-service:8000"
    os.environ["CHATBOT_SERVICE_URL"] = "http://chatbot-service:8000"
    os.environ["RAG_SERVICE_URL"] = "http://rag-service:8000"
    yield
    # Clean up after tests
    del os.environ["PDF_SERVICE_URL"]
    del os.environ["SENTIMENT_SERVICE_URL"]
    del os.environ["CHATBOT_SERVICE_URL"]
    del os.environ["RAG_SERVICE_URL"]

@pytest.fixture
def task_graph():
    return TaskGraph()

@pytest.fixture
def sample_tasks():
    return {
        "extract": SubTask(
            service=ServiceType.PDF_EXTRACTION,
            action="extract",
            data={"file": "test.pdf"},
            priority=1
        ),
        "analyze": SubTask(
            service=ServiceType.SENTIMENT,
            action="analyze",
            data={"text": "$result.extract.text"},
            priority=2,
            dependencies=["extract"]
        ),
        "store": SubTask(
            service=ServiceType.VECTOR_DB,
            action="store",
            data={
                "text": "$result.extract.text",
                "metadata": {"sentiment": "$result.analyze.sentiment"}
            },
            priority=3,
            dependencies=["extract", "analyze"]
        )
    }

@pytest.mark.asyncio
async def test_task_execution_order(task_graph, sample_tasks):
    """Test that tasks are executed in the correct order based on dependencies."""
    # Add tasks to graph
    for task_id, task in sample_tasks.items():
        task_graph.add_task(task_id, task)
    
    # Mock service responses
    mock_responses = {
        "extract": {"text": "test content"},
        "analyze": {"sentiment": "positive"},
        "store": {"status": "success"}
    }
    
    async def mock_service_call(url, **kwargs):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        action = url.split("/")[-1]
        mock_response.json.return_value = mock_responses[action]
        return mock_response
    
    with patch("httpx.AsyncClient.post", side_effect=mock_service_call):
        result = await task_graph.execute("test-correlation-id")
        assert result["status"] == "completed"
        assert len(result["results"]) > 0

@pytest.mark.asyncio
async def test_dependency_resolution(task_graph, sample_tasks):
    """Test that task dependencies are properly resolved."""
    # Add tasks to graph
    for task_id, task in sample_tasks.items():
        task_graph.add_task(task_id, task)
    
    # Mock service responses
    mock_responses = {
        "extract": {"text": "test content"},
        "analyze": {"sentiment": "positive"},
        "store": {"status": "success"}
    }
    
    async def mock_service_call(url, **kwargs):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        action = url.split("/")[-1]
        mock_response.json.return_value = mock_responses[action]
        return mock_response
    
    with patch("httpx.AsyncClient.post", side_effect=mock_service_call):
        result = await task_graph.execute("test-correlation-id")
        assert result["status"] == "completed"
        assert len(result["results"]) > 0

@pytest.mark.asyncio
async def test_task_failure_handling(task_graph):
    """Test handling of task failures."""
    # Add a task that will fail
    task_graph.add_task("fail", SubTask(
        service=ServiceType.PDF_EXTRACTION,
        action="extract",
        data={"file": "nonexistent.pdf"},
        priority=1
    ))
    
    async def mock_failed_call(*args, **kwargs):
        raise Exception("Service error")
    
    with patch("httpx.AsyncClient.post", side_effect=mock_failed_call):
        with pytest.raises(Exception) as exc_info:
            await task_graph.execute("test-correlation-id")
        assert "Some tasks failed" in str(exc_info.value)
        assert "fail" in task_graph.failed

@pytest.mark.asyncio
async def test_parallel_execution(task_graph):
    """Test that independent tasks are executed in parallel."""
    # Add two independent tasks
    task_graph.add_task("task1", SubTask(
        service=ServiceType.PDF_EXTRACTION,
        action="extract",
        data={"file": "test1.pdf"},
        priority=1
    ))
    task_graph.add_task("task2", SubTask(
        service=ServiceType.PDF_EXTRACTION,
        action="extract",
        data={"file": "test2.pdf"},
        priority=1
    ))
    
    async def mock_service_call(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        return mock_response
    
    with patch("httpx.AsyncClient.post", side_effect=mock_service_call):
        result = await task_graph.execute("test-correlation-id")
        assert len(result["results"]) == 2

@pytest.mark.asyncio
async def test_service_timeout_handling(task_graph):
    """Test handling of service timeouts."""
    task_graph.add_task("timeout", SubTask(
        service=ServiceType.RAG_SCRAPER,
        action="scrape",
        data={"url": "http://test.com"},
        priority=1
    ))
    
    async def mock_timeout(*args, **kwargs):
        raise TimeoutError("Service timeout")
    
    with patch("httpx.AsyncClient.post", side_effect=mock_timeout):
        with pytest.raises(Exception) as exc_info:
            await task_graph.execute("test-correlation-id")
        assert "timeout" in task_graph.failed

@pytest.mark.asyncio
async def test_correlation_id_propagation(task_graph, sample_tasks):
    """Test that correlation ID is propagated to service calls."""
    task_graph.add_task("test", sample_tasks["extract"])
    correlation_id = "test-correlation-id"
    
    async def mock_service_call(url, headers=None, **kwargs):
        assert headers["X-Correlation-ID"] == correlation_id
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        return mock_response
    
    with patch("httpx.AsyncClient.post", side_effect=mock_service_call):
        await task_graph.execute(correlation_id) 