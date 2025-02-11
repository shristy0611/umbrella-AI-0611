"""Test concurrent task submission."""

import asyncio
import base64
import logging
import time
from typing import Dict, Any
from src.orchestrator.orchestrator import Orchestrator
from src.services.service_registry import ServiceRegistry
import pytest

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_concurrent_tasks(test_runner):
    """Test concurrent task submission.
    
    Args:
        test_runner: Test runner fixture
    
    Returns:
        dict: Test results
    """
    start_time = time.time()
    try:
        # Read test PDF
        with open("test_data/sample.pdf", "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode()

        # Create multiple tasks
        tasks = []
        service_registry = test_runner['service_registry']
        
        # Create tasks for different services
        test_tasks = [
            {
                "service": "pdf_extraction",
                "request": {
                    "pdf_data": pdf_data,
                    "extract_text": True
                }
            },
            {
                "service": "sentiment_analysis",
                "request": {
                    "text": "Sample text for sentiment analysis",
                    "include_analysis": True
                }
            },
            {
                "service": "rag_scraper",
                "request": {
                    "query": "What are the main topics?",
                    "context": "Sample context for RAG analysis"
                }
            }
        ]

        # Process tasks concurrently
        async def process_task(task_info):
            service = service_registry.get_service(task_info["service"])
            if not service:
                raise ValueError(f"Service {task_info['service']} not found")
            return await service.process(task_info["request"])

        results = await asyncio.gather(
            *(process_task(task) for task in test_tasks),
            return_exceptions=True
        )

        # Validate results
        successful_tasks = 0
        failed_tasks = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_tasks.append({
                    "service": test_tasks[i]["service"],
                    "error": str(result)
                })
            elif result.get("status") == "success":
                successful_tasks += 1
            else:
                failed_tasks.append({
                    "service": test_tasks[i]["service"],
                    "error": result.get("error", "Unknown error")
                })

        passed = successful_tasks == len(test_tasks)

        return {
            "passed": passed,
            "duration": time.time() - start_time,
            "details": {
                "total_tasks": len(test_tasks),
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "error": None if passed else "Not all tasks completed successfully"
            }
        }

    except Exception as e:
        return {
            "passed": False,
            "duration": time.time() - start_time,
            "details": {"error": str(e)}
        } 