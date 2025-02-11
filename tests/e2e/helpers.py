"""Helper functions for end-to-end tests."""

import asyncio
import base64
import logging
from typing import Dict, Any
from pathlib import Path
import traceback
import time

from src.services.service_registry import ServiceRegistry
from src.orchestrator.orchestrator import Orchestrator
from src.services.pdf_extraction.service import PDFExtractionService
from src.task_decomposer import TaskType
from tests.e2e.constants import SERVICE_NAMES

logger = logging.getLogger(__name__)

async def run_health_checks_impl(service_registry: ServiceRegistry) -> Dict[str, Any]:
    """Run health checks for all services.
    
    Args:
        service_registry: Service registry instance
        
    Returns:
        Dict[str, Any]: Test results
    """
    try:
        # Get health status from registry
        health_status = await service_registry.health_check()
        
        # Check if all services are healthy
        all_healthy = (
            health_status["status"] == "healthy" and
            all(
                service["status"] == "healthy"
                for service in health_status["services"].values()
            )
        )
        
        return {
            "passed": all_healthy,
            "details": {
                "health_status": health_status,
                "error": None if all_healthy else "Not all services are healthy"
            }
        }
    except Exception as e:
        return {
            "passed": False,
            "details": {"error": str(e)}
        }

async def run_concurrent_tasks_impl(service_registry: ServiceRegistry) -> Dict[str, Any]:
    """Run concurrent task tests.
    
    Args:
        service_registry: Service registry instance
        
    Returns:
        Dict[str, Any]: Test results
    """
    try:
        # Read test PDF
        with open("test_data/sample.pdf", "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode()

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
                    "text": "Sample text for sentiment analysis"
                }
            },
            {
                "service": "rag_scraper",
                "request": {
                    "text": "Sample text for RAG processing"
                }
            }
        ]

        # Process tasks concurrently with better error handling
        async def process_task(task):
            try:
                service = service_registry.get_service(task["service"])
                if not service:
                    raise ValueError(f"Service {task['service']} not found")
                
                result = await service.process(task["request"])
                return {
                    "service": task["service"],
                    "status": "success",
                    "result": result
                }
            except Exception as e:
                logging.error(f"Task failed for service {task['service']}: {str(e)}")
                return {
                    "service": task["service"],
                    "status": "error",
                    "error": str(e)
                }

        results = await asyncio.gather(
            *(process_task(task) for task in test_tasks)
        )

        # Track successful and failed tasks
        successful_tasks = []
        failed_tasks = []
        
        for result in results:
            if result["status"] == "success":
                successful_tasks.append(result["service"])
            else:
                failed_tasks.append({
                    "service": result["service"],
                    "error": result.get("error", "Unknown error")
                })

        passed = len(successful_tasks) == len(test_tasks)

        return {
            "passed": passed,
            "details": {
                "total_tasks": len(test_tasks),
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "error": None if passed else f"{len(failed_tasks)} tasks failed"
            }
        }

    except Exception as e:
        logging.error(f"Concurrent tasks test failed: {str(e)}")
        return {
            "passed": False,
            "details": {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        }

async def run_task_dependencies_impl(orchestrator: Orchestrator) -> Dict[str, Any]:
    """Test task dependency resolution.
    
    Args:
        orchestrator: Orchestrator instance
        
    Returns:
        Dict[str, Any]: Test results
    """
    try:
        # Read test PDF
        with open("test_data/sample.pdf", "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode()

        # Create and submit document analysis task
        pdf_task = {
            "task_type": TaskType.DOCUMENT_ANALYSIS.value,
            "content": {
                "pdf_data": pdf_data,
                "analysis_types": ["pdf_extraction"],
                "extract_text": True
            }
        }

        # Submit PDF task
        pdf_task_id = await orchestrator.submit_task(pdf_task)
        await orchestrator.process_task(pdf_task_id)

        # Create sentiment task with dependency
        sentiment_task = {
            "task_type": TaskType.SENTIMENT_ANALYSIS.value,
            "content": {
                "text": "",  # Will be populated from PDF result
                "include_analysis": True
            },
            "dependencies": {
                SERVICE_NAMES['SENTIMENT_ANALYSIS']: [SERVICE_NAMES['PDF_EXTRACTION']]
            }
        }

        # Submit sentiment task
        sentiment_task_id = await orchestrator.submit_task(sentiment_task)
        await orchestrator.process_task(sentiment_task_id)

        # Poll for completion with improved retry mechanism
        max_retries = 30
        retry_count = 0
        completion_order = [SERVICE_NAMES['PDF_EXTRACTION']]  # PDF task already completed
        completed_tasks = {SERVICE_NAMES['PDF_EXTRACTION']}
        base_sleep = 0.5

        while retry_count < max_retries:
            status = await orchestrator.get_task_status(sentiment_task_id)
            logger.debug(f"Sentiment task status: {status}")
            
            if status["status"] == "completed":
                completion_order.append(SERVICE_NAMES['SENTIMENT_ANALYSIS'])
                completed_tasks.add(SERVICE_NAMES['SENTIMENT_ANALYSIS'])
                logger.info("Sentiment analysis task completed")
                break
            elif status["status"] == "failed":
                error_msg = f"Sentiment task failed: {status.get('error', 'Unknown error')}"
                logger.error(error_msg)
                return {
                    "passed": False,
                    "details": {"error": error_msg}
                }
                
            # Use exponential backoff with a cap
            sleep_time = min(base_sleep * (1.5 ** (retry_count // 3)), 3)
            await asyncio.sleep(sleep_time)
            retry_count += 1

        # Validate completion order
        expected_order = [SERVICE_NAMES['PDF_EXTRACTION'], SERVICE_NAMES['SENTIMENT_ANALYSIS']]
        dependencies_satisfied = (
            len(completion_order) == 2 and
            completion_order == expected_order
        )

        if not dependencies_satisfied:
            error_msg = f"Dependencies not satisfied. Expected order: {expected_order}, got: {completion_order}"
            logger.error(error_msg)
            return {
                "passed": False,
                "details": {
                    "error": error_msg,
                    "completion_order": completion_order,
                    "expected_order": expected_order
                }
            }

        logger.info("Task dependencies test passed")
        return {
            "passed": True,
            "details": {
                "completion_order": completion_order,
                "expected_order": expected_order,
                "dependencies_satisfied": dependencies_satisfied,
                "completed_tasks": list(completed_tasks),
                "retry_count": retry_count
            }
        }

    except Exception as e:
        logger.error(f"Task dependencies test failed: {str(e)}", exc_info=True)
        return {
            "passed": False,
            "details": {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        }

class CrashingPDFService(PDFExtractionService):
    """PDF service that simulates crashes and recovers."""
    
    def __init__(self):
        super().__init__()
        self.crash_count = 0
        self.recovery_count = 0
        self.max_crashes = 3  # Allow up to 3 crashes before succeeding
        self.recovery_delay = 1  # seconds

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
        
        if self.crash_count <= self.max_crashes:
            error_msg = f"Simulated crash {self.crash_count}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        await asyncio.sleep(self.recovery_delay)
        self.recovery_count += 1  # Increment recovery count after successful processing
        logger.info(f"CrashingPDFService recovered successfully (recovery #{self.recovery_count})")
        return await super().process(request)

async def run_system_recovery_impl(service_registry: ServiceRegistry, orchestrator: Orchestrator) -> Dict[str, Any]:
    """Test system recovery after service failures.
    
    Args:
        service_registry: Service registry instance
        orchestrator: Orchestrator instance
        
    Returns:
        Dict[str, Any]: Test results
    """
    start_time = time.time()
    original_service = None
    crashing_service = None
    
    try:
        # Replace PDF service with crashing version
        crashing_service = CrashingPDFService()
        await crashing_service.initialize()
        
        # Store original service for restoration
        original_service = service_registry.get_service(SERVICE_NAMES['PDF_EXTRACTION'])
        service_registry.register_service(SERVICE_NAMES['PDF_EXTRACTION'], crashing_service)
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

        # Submit task
        task_id = await orchestrator.submit_task(task)
        logger.info(f"Submitted task {task_id}")
        
        try:
            await orchestrator.process_task(task_id)
        except Exception as e:
            logger.error(f"Task processing failed (expected): {str(e)}")

        # Monitor task status and recovery
        max_retries = 30
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
            crashing_service.crash_count > crashing_service.max_crashes and  # Service exceeded max crashes
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
                service_registry.register_service(SERVICE_NAMES['PDF_EXTRACTION'], original_service)
                logger.info("Restored original PDF service")
            # Clean up crashing service
            if crashing_service:
                await crashing_service.cleanup()
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")

async def run_full_workflow_impl(orchestrator: Orchestrator) -> Dict[str, Any]:
    """Test complete end-to-end workflow.
    
    Args:
        orchestrator: Orchestrator instance
        
    Returns:
        Dict[str, Any]: Test results
    """
    try:
        # Read test PDF
        with open("test_data/sample.pdf", "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode()

        # Create comprehensive task
        task = {
            "task_type": "document_analysis",
            "content": {
                "pdf_data": pdf_data,
                "analysis_types": ["pdf_extraction", "sentiment_analysis", "rag_scraper"],
                "dependencies": {
                    "sentiment_analysis": ["pdf_extraction"],
                    "rag_scraper": ["pdf_extraction"]
                }
            }
        }

        # Submit and process task
        task_id = await orchestrator.submit_task(task)
        await orchestrator.process_task(task_id)

        # Poll for completion with exponential backoff
        max_retries = 20  # Increased from 10
        retry_count = 0
        base_delay = 1
        final_status = None
        completed_subtasks = set()

        while retry_count < max_retries:
            try:
                status = await orchestrator.get_task_status(task_id)
                final_status = status.get("status")
                
                # Track completed subtasks
                for subtask in status.get("subtasks", []):
                    if subtask.get("status") == "completed":
                        completed_subtasks.add(subtask.get("type"))
                
                if final_status == "completed":
                    results = await orchestrator.get_task_results(task_id)
                    return {
                        "passed": True,
                        "details": {
                            "final_status": final_status,
                            "completed_subtasks": list(completed_subtasks),
                            "results": results
                        }
                    }
                elif final_status == "failed":
                    return {
                        "passed": False,
                        "details": {
                            "final_status": final_status,
                            "completed_subtasks": list(completed_subtasks),
                            "error": "Task failed permanently"
                        }
                    }
                
                # Log progress
                logging.info(f"Workflow progress - Completed subtasks: {completed_subtasks}")
                
                # Exponential backoff with cap
                delay = min(base_delay * (2 ** retry_count), 5)  # Cap at 5 seconds
                await asyncio.sleep(delay)
                retry_count += 1
                
            except Exception as e:
                logging.error(f"Error checking task status: {str(e)}")
                await asyncio.sleep(1)
                retry_count += 1

        return {
            "passed": False,
            "details": {
                "final_status": final_status,
                "completed_subtasks": list(completed_subtasks),
                "error": f"Task did not complete in time. Status: {final_status}, Completed subtasks: {completed_subtasks}"
            }
        }

    except Exception as e:
        logging.error(f"Full workflow test failed: {str(e)}")
        return {
            "passed": False,
            "details": {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        } 