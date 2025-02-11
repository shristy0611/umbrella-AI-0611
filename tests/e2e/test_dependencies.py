"""Test task dependency resolution."""

import asyncio
import base64
import logging
import time
import traceback
from src.orchestrator.orchestrator import Orchestrator
from tests.e2e.constants import SERVICE_NAMES
from src.task_decomposer import TaskType

logger = logging.getLogger(__name__)

async def test_task_dependencies(orchestrator: Orchestrator):
    """Test task dependency resolution.
    
    Args:
        orchestrator: Initialized orchestrator
    
    Returns:
        dict: Test results
    """
    start_time = time.time()
    try:
        # Read test PDF
        with open("test_data/sample.pdf", "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode()

        # Create task with dependencies using consistent service names
        task = {
            "task_type": TaskType.DOCUMENT_ANALYSIS.value,
            "content": {
                "pdf_data": pdf_data,
                "analysis_types": ["sentiment"],
                "dependencies": {
                    SERVICE_NAMES['SENTIMENT_ANALYSIS']: [SERVICE_NAMES['PDF_EXTRACTION']]
                }
            }
        }

        # Submit task
        task_id = await orchestrator.submit_task(task)
        logger.info(f"Submitted task {task_id} for dependency testing")

        # Start task processing
        await orchestrator.process_task(task_id)
        logger.info(f"Started processing task {task_id}")

        # Poll for completion with improved retry mechanism
        max_retries = 30  # Increased from 20
        retry_count = 0
        completion_order = []
        base_sleep = 0.5

        while retry_count < max_retries:
            status = await orchestrator.get_task_status(task_id)
            logger.debug(f"Task {task_id} status: {status}")
            
            # Record completion of subtasks
            if "subtasks" in status:
                for subtask in status["subtasks"]:
                    if (
                        subtask["status"] == "completed" and
                        subtask["service"] not in completion_order
                    ):
                        completion_order.append(subtask["service"])
                        logger.info(f"Subtask completed: {subtask['service']}")
            
            if status["status"] == "completed":
                logger.info(f"Task {task_id} completed successfully")
                break
                
            # Use exponential backoff with a cap
            sleep_time = min(base_sleep * (1.5 ** (retry_count // 3)), 3)
            await asyncio.sleep(sleep_time)
            retry_count += 1

        # Get results
        results = await orchestrator.get_task_results(task_id)
        logger.info(f"Retrieved results for task {task_id}")

        # Validate results and dependency order
        pdf_extraction_completed = SERVICE_NAMES['PDF_EXTRACTION'] in completion_order
        sentiment_analysis_completed = SERVICE_NAMES['SENTIMENT_ANALYSIS'] in completion_order
        
        if not pdf_extraction_completed:
            error_msg = f"PDF extraction service ({SERVICE_NAMES['PDF_EXTRACTION']}) did not complete"
            logger.error(error_msg)
            return {
                "passed": False,
                "duration": time.time() - start_time,
                "details": {"error": error_msg}
            }
            
        if not sentiment_analysis_completed:
            error_msg = f"Sentiment analysis service ({SERVICE_NAMES['SENTIMENT_ANALYSIS']}) did not complete"
            logger.error(error_msg)
            return {
                "passed": False,
                "duration": time.time() - start_time,
                "details": {"error": error_msg}
            }

        # Check dependency order
        pdf_index = completion_order.index(SERVICE_NAMES['PDF_EXTRACTION'])
        sentiment_index = completion_order.index(SERVICE_NAMES['SENTIMENT_ANALYSIS'])
        
        if pdf_index >= sentiment_index:
            error_msg = "Dependencies not resolved in correct order"
            logger.error(error_msg)
            return {
                "passed": False,
                "duration": time.time() - start_time,
                "details": {
                    "error": error_msg,
                    "completion_order": completion_order
                }
            }

        return {
            "passed": True,
            "duration": time.time() - start_time,
            "details": {
                "completion_order": completion_order,
                "results": results,
                "retry_count": retry_count
            }
        }

    except Exception as e:
        logger.error(f"Task dependencies test failed: {str(e)}", exc_info=True)
        return {
            "passed": False,
            "duration": time.time() - start_time,
            "details": {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        } 