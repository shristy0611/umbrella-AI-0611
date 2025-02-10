import pytest
import os
from unittest.mock import patch, AsyncMock
from src.task_graph import TaskGraph
from src.task_decomposer import SubTask, ServiceType

@pytest.fixture
def graph():
    """Create a TaskGraph instance for testing."""
    return TaskGraph()

@pytest.fixture
def mock_env():
    """Set up mock environment variables."""
    env_vars = {
        "PDF_SERVICE_URL": "http://pdf:8001",
        "SENTIMENT_SERVICE_URL": "http://sentiment:8002",
        "CHATBOT_SERVICE_URL": "http://chatbot:8003",
        "SCRAPER_SERVICE_URL": "http://scraper:8004",
        "VECTOR_DB_URL": "http://vector_db:8005"
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars

@pytest.mark.asyncio
async def test_simple_task_execution(graph, mock_env):
    """Test execution of a single task without dependencies."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"text": "extracted text"}
        )
        
        # Add a simple task
        graph.add_task("extract", SubTask(
            service=ServiceType.PDF_EXTRACTION,
            action="extract",
            data={"file": "test.pdf"},
            priority=1
        ))
        
        # Execute graph
        result = await graph.execute("test-correlation-id")
        
        # Verify execution
        assert len(graph.completed) == 1
        assert len(graph.failed) == 0
        assert "extract" in graph.completed
        assert result["results"]["extract"]["text"] == "extracted text"
        
        # Verify service call
        mock_post.assert_called_once_with(
            "http://pdf:8001/extract",
            json={"file": "test.pdf"},
            headers={"X-Correlation-ID": "test-correlation-id"},
            timeout=30.0
        )

@pytest.mark.asyncio
async def test_dependent_tasks(graph, mock_env):
    """Test execution of tasks with dependencies."""
    with patch("httpx.AsyncClient.post") as mock_post:
        # Mock responses for different services
        async def mock_service_call(url, **kwargs):
            if "pdf" in url:
                return AsyncMock(
                    status_code=200,
                    json=lambda: {"text": "extracted text"}
                )
            elif "sentiment" in url:
                return AsyncMock(
                    status_code=200,
                    json=lambda: {"sentiment": "positive", "score": 0.8}
                )
            raise ValueError(f"Unexpected URL: {url}")
            
        mock_post.side_effect = mock_service_call
        
        # Add tasks with dependencies
        graph.add_task("extract", SubTask(
            service=ServiceType.PDF_EXTRACTION,
            action="extract",
            data={"file": "test.pdf"},
            priority=1
        ))
        graph.add_task("analyze", SubTask(
            service=ServiceType.SENTIMENT,
            action="analyze",
            data={"text": "$result.extract.text"},
            priority=2,
            dependencies=["extract"]
        ))
        
        # Execute graph
        result = await graph.execute("test-correlation-id")
        
        # Verify execution order
        assert len(graph.completed) == 2
        assert len(graph.failed) == 0
        assert list(graph.completed) == ["extract", "analyze"]
        
        # Verify results
        assert result["results"]["extract"]["text"] == "extracted text"
        assert result["results"]["analyze"]["sentiment"] == "positive"
        assert result["results"]["analyze"]["score"] == 0.8

@pytest.mark.asyncio
async def test_parallel_execution(graph, mock_env):
    """Test parallel execution of independent tasks."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"status": "success"}
        )
        
        # Add independent tasks
        graph.add_task("task1", SubTask(
            service=ServiceType.PDF_EXTRACTION,
            action="extract",
            data={"file": "test1.pdf"},
            priority=1
        ))
        graph.add_task("task2", SubTask(
            service=ServiceType.SENTIMENT,
            action="analyze",
            data={"text": "test text"},
            priority=1
        ))
        
        # Execute graph
        result = await graph.execute("test-correlation-id")
        
        # Verify parallel execution
        assert len(graph.completed) == 2
        assert len(graph.failed) == 0
        assert mock_post.call_count == 2

@pytest.mark.asyncio
async def test_task_failure_handling(graph, mock_env):
    """Test handling of task failures."""
    with patch("httpx.AsyncClient.post") as mock_post:
        # Mock a failed service call
        mock_post.side_effect = Exception("Service unavailable")
        
        # Add a task
        graph.add_task("failing_task", SubTask(
            service=ServiceType.PDF_EXTRACTION,
            action="extract",
            data={"file": "test.pdf"},
            priority=1
        ))
        
        # Execute graph and verify failure
        with pytest.raises(Exception, match="Some tasks failed"):
            await graph.execute("test-correlation-id")
        
        assert len(graph.completed) == 0
        assert len(graph.failed) == 1
        assert "failing_task" in graph.failed

@pytest.mark.asyncio
async def test_invalid_dependency_reference(graph, mock_env):
    """Test handling of invalid dependency references."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"status": "success"}
        )
        
        # Add task with invalid dependency reference
        graph.add_task("invalid_task", SubTask(
            service=ServiceType.SENTIMENT,
            action="analyze",
            data={"text": "$result.nonexistent.text"},
            priority=1
        ))
        
        # Execute graph and verify error
        with pytest.raises(ValueError, match="Referenced task nonexistent has not completed"):
            await graph.execute("test-correlation-id")

@pytest.mark.asyncio
async def test_missing_service_url(graph):
    """Test handling of missing service URL environment variables."""
    # Add task without setting environment variables
    graph.add_task("test_task", SubTask(
        service=ServiceType.PDF_EXTRACTION,
        action="extract",
        data={"file": "test.pdf"},
        priority=1
    ))
    
    # Execute graph and verify error
    with pytest.raises(ValueError, match="Missing environment variable: PDF_SERVICE_URL"):
        await graph.execute("test-correlation-id") 