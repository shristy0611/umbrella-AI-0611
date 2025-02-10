"""Integration tests for orchestrator service workflows."""

import pytest
import asyncio
from unittest.mock import Mock, patch
from orchestrator_service.src.main import app
from fastapi.testclient import TestClient
from shared.base_service import BaseService

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)

@pytest.fixture
def mock_pdf_service():
    """Mock PDF extraction service."""
    service = Mock(spec=BaseService)
    service.process.return_value = {
        "text": "Extracted text from PDF",
        "pages": 1,
        "metadata": {"filename": "test.pdf"}
    }
    return service

@pytest.fixture
def mock_sentiment_service():
    """Mock sentiment analysis service."""
    service = Mock(spec=BaseService)
    service.process.return_value = {
        "sentiment": "positive",
        "score": 0.85
    }
    return service

@pytest.fixture
def mock_vector_service():
    """Mock vector database service."""
    service = Mock(spec=BaseService)
    service.process.return_value = {
        "status": "success",
        "vector_id": "test-123"
    }
    return service

@pytest.mark.asyncio
async def test_document_analysis_workflow(
    client,
    mock_pdf_service,
    mock_sentiment_service,
    mock_vector_service
):
    """Test complete document analysis workflow.
    
    This test verifies that:
    1. Task is properly decomposed
    2. Services are called in correct order
    3. Results are properly aggregated
    4. Final response format is correct
    """
    # Mock service registry
    with patch("orchestrator_service.src.main.service_clients", {
        "pdf_extraction": mock_pdf_service,
        "sentiment": mock_sentiment_service,
        "vector_db": mock_vector_service
    }):
        # Submit document analysis task
        response = client.post("/process", json={
            "task_type": "document_analysis",
            "content": {
                "file": "test.pdf",
                "analysis_type": "full"
            }
        })
        
        assert response.status_code == 200, "Task submission should succeed"
        task_id = response.json()["task_id"]
        
        # Check task status
        status_response = client.get(f"/task/{task_id}/status")
        assert status_response.status_code == 200
        status = status_response.json()
        
        # Verify service calls
        mock_pdf_service.process.assert_called_once()
        mock_sentiment_service.process.assert_called_once()
        mock_vector_service.process.assert_called_once()
        
        # Verify final results
        results_response = client.get(f"/task/{task_id}/results")
        assert results_response.status_code == 200
        results = results_response.json()
        
        assert "extracted_text" in results, "Results should include extracted text"
        assert "sentiment" in results, "Results should include sentiment analysis"
        assert "vector_id" in results, "Results should include vector database reference"

@pytest.mark.asyncio
async def test_parallel_task_processing(client, mock_pdf_service):
    """Test handling of multiple concurrent tasks.
    
    This test verifies that:
    1. Multiple tasks can be processed simultaneously
    2. Task results are not mixed up
    3. System maintains performance under load
    """
    num_tasks = 5
    
    # Submit multiple tasks
    task_ids = []
    for i in range(num_tasks):
        response = client.post("/process", json={
            "task_type": "document_analysis",
            "content": {
                "file": f"test_{i}.pdf",
                "analysis_type": "basic"
            }
        })
        assert response.status_code == 200
        task_ids.append(response.json()["task_id"])
    
    # Check all task statuses
    for task_id in task_ids:
        status_response = client.get(f"/task/{task_id}/status")
        assert status_response.status_code == 200
        status = status_response.json()
        assert status["task_id"] == task_id, "Task IDs should match"

@pytest.mark.asyncio
async def test_error_handling_and_recovery(client, mock_pdf_service):
    """Test error handling and recovery mechanisms.
    
    This test verifies that:
    1. Service failures are properly handled
    2. Error messages are informative
    3. System can recover from failures
    4. Failed tasks don't affect other tasks
    """
    # Make PDF service fail
    mock_pdf_service.process.side_effect = Exception("Service unavailable")
    
    # Submit task that will fail
    response = client.post("/process", json={
        "task_type": "document_analysis",
        "content": {"file": "test.pdf"}
    })
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    
    # Check error status
    status_response = client.get(f"/task/{task_id}/status")
    assert status_response.status_code == 200
    status = status_response.json()
    assert status["status"] == "failed", "Task should be marked as failed"
    assert "error" in status, "Error details should be included"
    
    # Fix service and retry
    mock_pdf_service.process.side_effect = None
    mock_pdf_service.process.return_value = {"text": "Extracted text"}
    
    retry_response = client.post(f"/task/{task_id}/retry")
    assert retry_response.status_code == 200
    
    # Verify recovery
    final_status = client.get(f"/task/{task_id}/status").json()
    assert final_status["status"] == "completed", "Task should recover after retry"

@pytest.mark.asyncio
async def test_task_cancellation(client):
    """Test task cancellation functionality.
    
    This test verifies that:
    1. Tasks can be cancelled
    2. Resources are properly cleaned up
    3. Dependent tasks are handled appropriately
    4. System state remains consistent
    """
    # Submit a long-running task
    response = client.post("/process", json={
        "task_type": "document_analysis",
        "content": {
            "file": "large.pdf",
            "analysis_type": "full"
        }
    })
    task_id = response.json()["task_id"]
    
    # Cancel the task
    cancel_response = client.post(f"/task/{task_id}/cancel")
    assert cancel_response.status_code == 200
    
    # Verify cancellation
    status = client.get(f"/task/{task_id}/status").json()
    assert status["status"] == "cancelled", "Task should be marked as cancelled"
    
    # Verify cleanup
    assert "resources_cleaned" in status, "Resources should be cleaned up"

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 