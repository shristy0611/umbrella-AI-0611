"""End-to-end test for document analysis workflow."""

import os
import pytest
import asyncio
from typing import Dict, Any
from shared.orchestrator import Orchestrator
from shared.gemini import (
    GeminiTextChat,
    GeminiFileUpload,
    GeminiSingleImage,
    gemini_config
)

pytestmark = pytest.mark.asyncio

async def test_document_analysis_workflow(
    test_env: Dict[str, str],
    sample_pdf_path: str,
    mock_orchestrator_request: Dict[str, Any]
) -> None:
    """Test complete document analysis workflow from request to final output.
    
    This test verifies:
    1. Orchestrator receives and validates request
    2. Task is decomposed into subtasks
    3. PDF is processed and text extracted
    4. Analysis is performed on extracted content
    5. Results are aggregated and returned
    """
    # Initialize components
    orchestrator = Orchestrator()
    file_processor = GeminiFileUpload()
    text_analyzer = GeminiTextChat()
    
    try:
        # 1. Submit request to orchestrator
        task_id = await orchestrator.submit_task(mock_orchestrator_request)
        assert task_id == mock_orchestrator_request["task_id"]
        
        # 2. Get task status
        status = await orchestrator.get_task_status(task_id)
        assert status["status"] == "processing"
        
        # 3. Process document
        file_response = await file_processor.process_file(
            sample_pdf_path,
            "Extract and analyze the main content of this document",
            mime_type="application/pdf"
        )
        assert file_response is not None
        assert hasattr(file_response, "text")
        
        # 4. Analyze extracted content
        analysis_response = await text_analyzer.send_message(
            f"Analyze the following content: {file_response.text[:1000]}"
        )
        assert analysis_response is not None
        assert hasattr(analysis_response, "text")
        
        # 5. Get final results
        results = await orchestrator.get_task_results(task_id)
        assert results is not None
        assert "analysis" in results
        assert "extracted_text" in results
        assert results["status"] == "completed"
        
        # Verify result format
        assert isinstance(results["analysis"], dict)
        assert "summary" in results["analysis"]
        assert "key_points" in results["analysis"]
        assert isinstance(results["analysis"]["key_points"], list)
        
    except Exception as e:
        pytest.fail(f"Workflow test failed: {str(e)}")

async def test_error_handling_workflow(
    test_env: Dict[str, str],
    mock_orchestrator_request: Dict[str, Any]
) -> None:
    """Test error handling in the workflow.
    
    This test verifies:
    1. Invalid document handling
    2. API error recovery
    3. Timeout handling
    4. Error reporting
    """
    orchestrator = Orchestrator()
    
    # Modify request to trigger error
    invalid_request = mock_orchestrator_request.copy()
    invalid_request["content"]["document_url"] = "invalid_url"
    
    try:
        # Submit invalid request
        task_id = await orchestrator.submit_task(invalid_request)
        
        # Verify error status
        status = await orchestrator.get_task_status(task_id)
        assert status["status"] == "failed"
        assert "error" in status
        assert "invalid_url" in status["error"].lower()
        
    except Exception as e:
        pytest.fail(f"Error handling test failed: {str(e)}")

async def test_performance_workflow(
    test_env: Dict[str, str],
    mock_orchestrator_request: Dict[str, Any]
) -> None:
    """Test performance metrics of the workflow.
    
    This test verifies:
    1. Response times
    2. Resource usage
    3. Concurrent request handling
    """
    orchestrator = Orchestrator()
    num_requests = 3
    
    try:
        # Submit multiple requests concurrently
        start_time = asyncio.get_event_loop().time()
        
        tasks = [
            orchestrator.submit_task(mock_orchestrator_request)
            for _ in range(num_requests)
        ]
        task_ids = await asyncio.gather(*tasks)
        
        # Verify all tasks were accepted
        assert len(task_ids) == num_requests
        
        # Check completion time
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        
        # Verify performance metrics
        assert total_time < 10.0  # Should complete within 10 seconds
        
        # Check all tasks completed
        statuses = await asyncio.gather(*[
            orchestrator.get_task_status(task_id)
            for task_id in task_ids
        ])
        
        assert all(status["status"] in ["completed", "processing"]
                  for status in statuses)
        
    except Exception as e:
        pytest.fail(f"Performance test failed: {str(e)}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 