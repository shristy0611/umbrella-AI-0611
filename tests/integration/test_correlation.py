"""Integration tests for correlation ID propagation."""

import pytest
import uuid
import httpx
import logging
from fastapi.testclient import TestClient
from src.utils.logging import setup_logging, get_correlation_id
from unittest.mock import patch

# Test logger
logger = logging.getLogger(__name__)

@pytest.fixture
def test_client():
    """Create a test client with correlation ID middleware."""
    from fastapi import FastAPI
    from src.middleware.correlation import CorrelationIdMiddleware
    
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    
    return TestClient(app)

@pytest.fixture
def mock_services():
    """Mock service endpoints for testing."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": "success"}
        yield mock_post

@pytest.mark.asyncio
async def test_correlation_id_propagation(test_client, mock_services, caplog):
    """Test correlation ID propagation through the system."""
    # Set up logging
    setup_logging("test_service")
    
    # Generate test correlation ID
    test_correlation_id = str(uuid.uuid4())
    
    # Make request with correlation ID
    response = test_client.post(
        "/process",
        json={"task": "test_task"},
        headers={"X-Correlation-ID": test_correlation_id}
    )
    
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == test_correlation_id
    
    # Verify correlation ID in service calls
    for call in mock_services.call_args_list:
        headers = call.kwargs.get("headers", {})
        assert headers.get("X-Correlation-ID") == test_correlation_id
    
    # Verify correlation ID in logs
    for record in caplog.records:
        assert hasattr(record, "correlation_id")
        assert record.correlation_id == test_correlation_id

@pytest.mark.asyncio
async def test_correlation_id_generation(test_client, caplog):
    """Test automatic correlation ID generation."""
    # Set up logging
    setup_logging("test_service")
    
    # Make request without correlation ID
    response = test_client.post(
        "/process",
        json={"task": "test_task"}
    )
    
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    generated_id = response.headers["X-Correlation-ID"]
    
    # Verify generated ID in logs
    for record in caplog.records:
        assert hasattr(record, "correlation_id")
        assert record.correlation_id == generated_id

@pytest.mark.asyncio
async def test_correlation_id_context(test_client):
    """Test correlation ID context management."""
    # Set up logging
    setup_logging("test_service")
    
    test_correlation_id = str(uuid.uuid4())
    
    async def test_endpoint():
        # Verify correlation ID is available in context
        assert get_correlation_id() == test_correlation_id
        return {"status": "success"}
    
    app = test_client.app
    app.post("/test")(test_endpoint)
    
    response = test_client.post(
        "/test",
        headers={"X-Correlation-ID": test_correlation_id}
    )
    
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_correlation_id_in_error_handling(test_client, caplog):
    """Test correlation ID presence in error logs."""
    # Set up logging
    setup_logging("test_service")
    
    test_correlation_id = str(uuid.uuid4())
    
    async def error_endpoint():
        logger.error("Test error")
        raise ValueError("Test error")
    
    app = test_client.app
    app.post("/error")(error_endpoint)
    
    response = test_client.post(
        "/error",
        headers={"X-Correlation-ID": test_correlation_id}
    )
    
    assert response.status_code == 500
    
    # Verify correlation ID in error logs
    error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_logs) > 0
    for record in error_logs:
        assert hasattr(record, "correlation_id")
        assert record.correlation_id == test_correlation_id 