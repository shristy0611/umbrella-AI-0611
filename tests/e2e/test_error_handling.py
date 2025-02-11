"""Test error handling and retry mechanism."""

import asyncio
import logging
import time
import base64
from unittest.mock import patch
from src.services.pdf_extraction.service import PDFExtractionService
from src.services.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)

class FailingPDFService(PDFExtractionService):
    """PDF service that fails on first attempt."""

    def __init__(self):
        """Initialize service."""
        super().__init__()
        self.attempt_count = 0

    async def process(self, request):
        """Process request with simulated failure."""
        self.attempt_count += 1
        if self.attempt_count == 1:
            raise Exception("Simulated first attempt failure")
        return await super().process(request)

async def test_error_handling(service_registry: ServiceRegistry):
    """Test error handling and retry mechanism.
    
    Args:
        service_registry: Service registry
    
    Returns:
        dict: Test results
    """
    start_time = time.time()
    try:
        # Replace PDF service with failing version
        failing_service = FailingPDFService()
        await failing_service.initialize()
        service_registry.register_service("pdf_extraction", failing_service)

        # Create request
        with open("test_data/sample.pdf", "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode()

        request = {
            "pdf_data": pdf_data,
            "extract_text": True
        }

        # Process request (should fail first time)
        result = None
        error = None
        retry_count = 0
        max_retries = 3

        for attempt in range(max_retries):
            try:
                result = await failing_service.process(request)
                break
            except Exception as e:
                error = str(e)
                retry_count += 1
                await asyncio.sleep(1)  # Wait before retry

        # Validate results
        passed = (
            result is not None and
            result["status"] == "success" and
            failing_service.attempt_count > 1  # Confirms retry occurred
        )

        return {
            "passed": passed,
            "duration": time.time() - start_time,
            "details": {
                "attempts": failing_service.attempt_count,
                "final_result": result,
                "initial_error": error,
                "retry_count": retry_count,
                "error": None if passed else "Retry mechanism failed"
            }
        }

    except Exception as e:
        return {
            "passed": False,
            "duration": time.time() - start_time,
            "details": {"error": str(e)}
        }

    finally:
        # Restore original service
        original_service = PDFExtractionService()
        await original_service.initialize()
        service_registry.register_service("pdf_extraction", original_service) 