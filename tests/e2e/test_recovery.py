"""Test system recovery and resilience."""

import asyncio
import logging
import time
import base64
import traceback
from src.orchestrator.orchestrator import Orchestrator
from src.services.pdf_extraction.service import PDFExtractionService
from src.shared.service_registry import ServiceRegistry
from src.task_decomposer import TaskType
from typing import Dict, Any

logger = logging.getLogger(__name__)

class CrashingPDFService(PDFExtractionService):
    """PDF service that simulates crashes and recovers."""

    def __init__(self):
        """Initialize crashing service."""
        super().__init__()
        self.crash_count = 0
        self.recovery_count = 0
        self.max_crashes = 3  # Allow up to 3 crashes before succeeding

    async def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process request with simulated crashes.
        
        Args:
            request: Request to process
            
        Returns:
            Dict[str, Any]: Processing results
            
        Raises:
            RuntimeError: On simulated crash
        """
        self.crash_count += 1
        logger.info(f"Processing attempt {self.crash_count} in CrashingPDFService")
        
        await asyncio.sleep(1)  # Simulate work
        
        if self.crash_count <= self.max_crashes:
            error_msg = f"Simulated crash {self.crash_count}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        self.recovery_count += 1
        logger.info("CrashingPDFService recovered successfully")
        return await super().process(request)

async def test_system_recovery(service_registry: ServiceRegistry, orchestrator: Orchestrator):
    """Test system recovery and resilience.
    
    Args:
        service_registry: Service registry
        orchestrator: Orchestrator
    
    Returns:
        dict: Test results
    """
    start_time = time.time()
    original_service = None
    crashing_service = None
    
    try:
        # Replace PDF service with crashing version
        crashing_service = CrashingPDFService()
        await crashing_service.initialize()
        
        # Store original service for restoration
        original_service = service_registry.get_service("pdf_extraction")
        service_registry.register_service("pdf_extraction", crashing_service)
        logger.info("Registered crashing PDF service")

        # Create task
        with open("test_data/sample.pdf", "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode()

        task = {
            "task_type": TaskType.DOCUMENT_ANALYSIS.value,
            "content": {
                "pdf_data": pdf_data,
                "analysis_types": ["pdf_extraction"]
            }
        }

        # Submit and process task
        task_id = await orchestrator.submit_task(task)
        logger.info(f"Submitted task {task_id}")
        
        try:
            await orchestrator.process_task(task_id)
        except Exception as e:
            logger.error(f"Task processing failed (expected): {str(e)}")

        # Monitor task status and recovery
        max_retries = 30  # Increased from 20
        retry_count = 0
        status_history = []
        final_status = None
        base_sleep = 0.5

        while retry_count < max_retries:
            status = await orchestrator.get_task_status(task_id)
            status_history.append(status)
            logger.debug(f"Task status: {status['status']}")
            
            if status["status"] == "completed":
                final_status = status
                logger.info("Task completed successfully")
                break
            elif status["status"] == "failed":
                # Retry the task
                logger.info("Retrying failed task")
                try:
                    await orchestrator.process_task(task_id)
                except Exception as e:
                    logger.error(f"Task retry failed (expected): {str(e)}")
                
            # Use exponential backoff with a cap
            sleep_time = min(base_sleep * (1.5 ** (retry_count // 3)), 3)
            await asyncio.sleep(sleep_time)
            retry_count += 1

        # Get final results if completed
        results = None
        if final_status and final_status["status"] == "completed":
            results = await orchestrator.get_task_results(task_id)
            logger.info("Retrieved final results")

        # Validate recovery
        passed = (
            crashing_service.crash_count > 0 and  # Service crashed
            crashing_service.recovery_count > 0 and  # Service recovered
            final_status is not None and
            final_status["status"] == "completed" and  # Task completed
            results is not None  # Task succeeded
        )

        if passed:
            logger.info("System recovery test passed")
        else:
            logger.error("System recovery test failed")

        return {
            "passed": passed,
            "duration": time.time() - start_time,
            "details": {
                "crash_count": crashing_service.crash_count,
                "recovery_count": crashing_service.recovery_count,
                "status_history": status_history,
                "final_status": final_status,
                "results": results,
                "error": None if passed else "System did not recover properly"
            }
        }

    except Exception as e:
        logger.error(f"System recovery test failed with error: {str(e)}", exc_info=True)
        return {
            "passed": False,
            "duration": time.time() - start_time,
            "details": {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        }

    finally:
        try:
            # Restore original service if it exists
            if original_service:
                service_registry.register_service("pdf_extraction", original_service)
                logger.info("Restored original PDF service")
            # Clean up crashing service
            if crashing_service:
                await crashing_service.cleanup()
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}") 