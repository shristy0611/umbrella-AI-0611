"""Test full end-to-end workflow."""

import asyncio
import logging
import time
import base64
import traceback
from src.app import app
from fastapi.testclient import TestClient
from src.orchestrator.orchestrator import Orchestrator
from src.shared.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)

async def test_full_workflow(orchestrator: Orchestrator):
    """Test full end-to-end workflow.
    
    Args:
        orchestrator: Initialized orchestrator
    
    Returns:
        dict: Test results
    """
    start_time = time.time()
    try:
        # Create test client
        client = TestClient(app)

        # Step 1: Upload PDF
        with open("test_data/sample.pdf", "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        if response.status_code != 200:
            return {
                "passed": False,
                "duration": time.time() - start_time,
                "details": {
                    "step": "upload",
                    "error": f"Upload failed: {response.json()}"
                }
            }

        file_id = response.json()["file_id"]

        # Step 2: Submit comprehensive analysis task
        task = {
            "task_type": "document_analysis",
            "content": {
                "file_id": file_id,
                "analysis_types": [
                    "pdf_extraction",
                    "sentiment",
                    "summary",
                    "topics"
                ]
            }
        }

        # Submit and process task
        task_id = await orchestrator.submit_task(task)
        await orchestrator.process_task(task_id)

        # Step 3: Poll for completion with increased timeout
        max_retries = 60  # Increased from 30 to 60
        retry_count = 0
        final_status = None

        while retry_count < max_retries:
            status = await orchestrator.get_task_status(task_id)
            final_status = status
            
            if status["status"] == "completed":
                break
                
            # Add exponential backoff
            await asyncio.sleep(min(1 * (2 ** (retry_count // 5)), 5))
            retry_count += 1

        if not final_status or final_status["status"] != "completed":
            return {
                "passed": False,
                "duration": time.time() - start_time,
                "details": {
                    "step": "processing",
                    "status": final_status,
                    "error": "Task did not complete in time",
                    "retry_count": retry_count
                }
            }

        # Step 4: Get and validate results
        results = await orchestrator.get_task_results(task_id)

        # Validate all components
        validations = {
            "pdf_extraction": "pdf_extraction" in results,
            "sentiment": "sentiment_analysis" in results,
            "summary": "summary" in results,
            "topics": "topics" in results
        }

        passed = all(validations.values())

        return {
            "passed": passed,
            "duration": time.time() - start_time,
            "details": {
                "file_id": file_id,
                "task_id": task_id,
                "validations": validations,
                "results": results,
                "status": final_status,
                "retry_count": retry_count,
                "error": None if passed else "Missing required components in results"
            }
        }

    except Exception as e:
        return {
            "passed": False,
            "duration": time.time() - start_time,
            "details": {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        } 