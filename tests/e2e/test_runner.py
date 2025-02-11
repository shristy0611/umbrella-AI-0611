"""End-to-end test runner for UMBRELLA-AI."""

import asyncio
import logging
import json
import os
import time
from datetime import datetime
from typing import Dict, Any, List, AsyncGenerator
import aiohttp
import markdown
import base64
from pathlib import Path
import traceback
from dataclasses import asdict
from enum import Enum
import pytest
from src.services.service_registry import ServiceRegistry
from src.orchestrator.orchestrator import Orchestrator
from src.services.pdf_extraction.service import PDFExtractionService
from src.services.sentiment_analysis.service import SentimentAnalysisService
from src.services.chatbot.service import ChatbotService
from src.services.rag_scraper.service import RAGScraperService
from src.services.recommendation.service import RecommendationService
from tests.e2e.constants import SERVICE_NAMES
from tests.e2e.helpers import (
    run_health_checks_impl,
    run_concurrent_tasks_impl,
    run_task_dependencies_impl,
    run_system_recovery_impl,
    run_full_workflow_impl
)

# Import test cases
from .test_concurrent import test_concurrent_tasks as run_concurrent_tasks
from .test_invalid_file import test_invalid_file_upload as run_invalid_file_upload
from .test_dependencies import test_task_dependencies as run_task_dependencies
from .test_error_handling import test_error_handling as run_error_handling
from .test_health import test_health_checks as run_health_checks
from .test_full_workflow import test_full_workflow as run_full_workflow
from .test_recovery import test_system_recovery as run_system_recovery

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
async def test_runner(service_registry: ServiceRegistry):
    """Create a test runner instance with initialized services."""
    services = {}
    try:
        # Initialize services
        services = {
            SERVICE_NAMES['PDF_EXTRACTION']: PDFExtractionService(),
            SERVICE_NAMES['SENTIMENT_ANALYSIS']: SentimentAnalysisService(),
            SERVICE_NAMES['CHATBOT']: ChatbotService(),
            SERVICE_NAMES['RAG_SCRAPER']: RAGScraperService(),
            SERVICE_NAMES['RECOMMENDATION']: RecommendationService()
        }
        
        # Initialize and register each service
        for name, service in services.items():
            await service.initialize()
            service_registry.register_service(name, service)
            logger.info(f"Initialized and registered service: {name}")
        
        yield {
            'service_registry': service_registry,
            **services
        }
        
    except Exception as e:
        logger.error(f"Error setting up test runner: {str(e)}")
        raise
    finally:
        # Cleanup services
        for service in services.values():
            try:
                await service.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up service: {str(e)}")

class TestRunner:
    """Test runner for end-to-end tests."""

    def __init__(self):
        """Initialize test runner with necessary services."""
        # Initialize services
        self.service_registry = ServiceRegistry()
        self.pdf_service = PDFExtractionService()
        self.sentiment_service = SentimentAnalysisService()
        self.chatbot_service = ChatbotService()
        self.rag_service = RAGScraperService()
        self.recommendation_service = RecommendationService()
        
        # Register services
        self.service_registry.register_service("pdf_extraction", self.pdf_service)
        self.service_registry.register_service("sentiment_analysis", self.sentiment_service)
        self.service_registry.register_service("chatbot", self.chatbot_service)
        self.service_registry.register_service("rag_scraper", self.rag_service)
        self.service_registry.register_service("recommendation", self.recommendation_service)
        
        # Initialize orchestrator
        logging.info("Initializing orchestrator...")
        self.orchestrator = Orchestrator(self.service_registry)
        logging.info("Orchestrator initialized successfully")

        # Initialize test results
        self.results = []

    async def initialize(self):
        """Initialize services."""
        # Initialize services
        self.pdf_service = PDFExtractionService()
        self.sentiment_service = SentimentAnalysisService()
        self.chatbot_service = ChatbotService()
        self.rag_service = RAGScraperService()
        self.recommendation_service = RecommendationService()

        # Register services
        self.service_registry.register_service("pdf_extraction", self.pdf_service)
        self.service_registry.register_service("sentiment_analysis", self.sentiment_service)
        self.service_registry.register_service("chatbot", self.chatbot_service)
        self.service_registry.register_service("rag_scraper", self.rag_service)
        self.service_registry.register_service("recommendation", self.recommendation_service)

        # Initialize orchestrator
        self.orchestrator.service_registry = self.service_registry

        # Initialize all services
        await self.service_registry.initialize()
        await self.orchestrator.initialize()

    async def cleanup(self):
        """Clean up resources."""
        await self.service_registry.cleanup()
        await self.orchestrator.cleanup()

    def record_test_result(self, test_name: str, passed: bool, duration: float, details: Dict[str, Any]):
        """Record test result."""
        self.results.append({
            "test_name": test_name,
            "passed": passed,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "details": self._serialize_details(details)
        })
        
        # Update summary
        self.report_data["summary"]["total_tests"] += 1
        if passed:
            self.report_data["summary"]["passed_tests"] += 1
        else:
            self.report_data["summary"]["failed_tests"] += 1
        self.report_data["summary"]["total_time"] += duration

        # Add test case details
        self.report_data["test_cases"].append({
            "name": test_name,
            "status": "PASS" if passed else "FAIL",
            "duration": f"{duration:.2f}s",
            "details": details
        })

    def _serialize_details(self, obj: Any) -> Any:
        """Recursively serialize objects to JSON-compatible format.
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON-serializable object
        """
        if hasattr(obj, "to_dict"):
            return self._serialize_details(obj.to_dict())
        elif hasattr(obj, "value") and isinstance(obj, Enum):  # Handle Enum TaskStatus
            return str(obj.value)
        elif hasattr(obj, "__dataclass_fields__"):  # Handle dataclass TaskStatus
            return self._serialize_details(asdict(obj))
        elif hasattr(obj, "__dict__"):
            return self._serialize_details(obj.__dict__)
        elif isinstance(obj, (list, tuple)):
            return [self._serialize_details(item) for item in obj]
        elif isinstance(obj, dict):
            return {
                str(k): self._serialize_details(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, datetime):  # Handle datetime objects
            return obj.isoformat()
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            return str(obj)

    async def run_all_tests(self):
        """Run all test cases and record results."""
        results = []
        
        test_cases = [
            ("Health Checks", self.test_health_checks),
            ("Invalid File Upload", self.test_invalid_file_upload),
            ("Task Dependencies", self.test_task_dependencies),
            ("Concurrent Tasks", self.test_concurrent_tasks),
            ("Error Handling", self.test_error_handling),
            ("System Recovery", self.test_system_recovery),
            ("Full Workflow", self.test_full_workflow)
        ]
        
        for test_name, test_func in test_cases:
            try:
                start_time = time.time()
                result = await test_func()
                duration = time.time() - start_time
                
                results.append({
                    "test_name": test_name,
                    "passed": True,
                    "duration": duration,
                    "details": result
                })
                logging.info(f"Test {test_name} passed in {duration:.2f}s")
                
            except Exception as e:
                logging.error(f"Test {test_name} failed: {str(e)}")
                results.append({
                    "test_name": test_name,
                    "passed": False,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
        
        # Generate report
        report_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        report = {
            "timestamp": report_time,
            "total_tests": len(test_cases),
            "passed_tests": sum(1 for r in results if r.get("passed", False)),
            "failed_tests": sum(1 for r in results if not r.get("passed", False)),
            "results": results
        }
        
        # Save report
        os.makedirs("reports", exist_ok=True)
        
        # Save as JSON
        json_path = f"reports/test_report_{report_time}.json"
        with open(json_path, "w") as f:
            json.dump(report, f, indent=2)
        
        # Save as Markdown
        md_path = f"reports/test_report_{report_time}.md"
        with open(md_path, "w") as f:
            f.write("# UMBRELLA-AI Test Report\n\n")
            f.write(f"Generated at: {report_time}\n\n")
            f.write(f"Total Tests: {report['total_tests']}\n")
            f.write(f"Passed: {report['passed_tests']}\n")
            f.write(f"Failed: {report['failed_tests']}\n\n")
            
            f.write("## Test Results\n\n")
            for result in results:
                f.write(f"### {result['test_name']}\n")
                f.write(f"Status: {'✅ Passed' if result.get('passed', False) else '❌ Failed'}\n")
                if "duration" in result:
                    f.write(f"Duration: {result['duration']:.2f}s\n")
                if "error" in result:
                    f.write(f"\nError: {result['error']}\n")
                    f.write("\nTraceback:\n```\n")
                    f.write(result['traceback'])
                    f.write("```\n")
                if "details" in result:
                    f.write("\nDetails:\n```json\n")
                    f.write(json.dumps(result['details'], indent=2))
                    f.write("\n```\n")
                f.write("\n---\n\n")
        
        return report

    async def test_health_checks(self):
        """Test health check endpoints."""
        start_time = time.time()
        try:
            # Check service registry health
            registry_health = await self.service_registry.health_check()
            
            # Check individual service health
            service_health = {}
            for name, service in self.service_registry.list_services().items():
                service_health[name] = await service.health_check()
            
            # Validate all services are healthy
            all_healthy = (
                registry_health["status"] == "healthy" and
                all(h["status"] == "healthy" for h in service_health.values())
            )
            
            return {
                "passed": all_healthy,
                "duration": time.time() - start_time,
                "details": {
                    "registry_health": registry_health,
                    "service_health": service_health,
                    "error": None if all_healthy else "Not all services are healthy"
                }
            }
            
        except Exception as e:
            return {
                "passed": False,
                "duration": time.time() - start_time,
                "details": {"error": str(e)}
            }

    async def test_invalid_file_upload(self):
        """Test handling of invalid file uploads."""
        # Create a temporary invalid file
        test_file_path = "test_data/invalid.exe"
        os.makedirs(os.path.dirname(test_file_path), exist_ok=True)
        
        with open(test_file_path, "w") as f:
            f.write("This is not a PDF file")
        
        try:
            async with aiohttp.ClientSession() as session:
                with open(test_file_path, "rb") as f:
                    data = aiohttp.FormData()
                    data.add_field("file",
                                 f,
                                 filename="invalid.exe",
                                 content_type="application/octet-stream")
                    
                    async with session.post("http://localhost:8000/api/v1/upload", data=data) as response:
                        status = response.status
                        text = await response.text()
                        
                        return {
                            "passed": status == 400,
                            "status": status,
                            "response": text
                        }
        finally:
            # Cleanup
            if os.path.exists(test_file_path):
                os.remove(test_file_path)

    async def test_task_dependencies(self):
        """Test task dependency resolution."""
        # Read sample PDF
        with open("test_data/sample.pdf", "rb") as f:
            pdf_content = base64.b64encode(f.read()).decode()
        
        # Create task with dependencies
        task = {
            "task_type": "document_analysis",
            "content": {
                "file_content": pdf_content,
                "analysis_types": ["sentiment"],
                "dependencies": {
                    "sentiment": ["pdf_extraction"]
                }
            }
        }
        
        # Submit task
        task_id = await self.orchestrator.submit_task(task)
        
        # Poll for completion
        max_retries = 20
        retry_count = 0
        completion_order = []
        
        while retry_count < max_retries:
            status = await self.orchestrator.get_task_status(task_id)
            
            if status["status"] == "completed":
                break
                
            if status.get("completed_subtasks"):
                for subtask in status["completed_subtasks"]:
                    if subtask not in completion_order:
                        completion_order.append(subtask)
            
            retry_count += 1
            await asyncio.sleep(1)
        
        results = await self.orchestrator.get_task_results(task_id)
        
        return {
            "passed": len(completion_order) == 2 and 
                     completion_order.index("pdf_extraction") < completion_order.index("sentiment"),
            "completion_order": completion_order,
            "results": results,
            "retry_count": retry_count
        }

    async def test_concurrent_tasks(self):
        """Test concurrent task submission and processing."""
        # Read sample PDF
        with open("test_data/sample.pdf", "rb") as f:
            pdf_content = base64.b64encode(f.read()).decode()
        
        # Create multiple tasks
        tasks = []
        for i in range(3):
            task = {
                "task_type": "document_analysis",
                "content": {
                    "file_content": pdf_content,
                    "analysis_types": ["sentiment", "summary"],
                    "task_id": f"concurrent_task_{i}"
                }
            }
            tasks.append(task)
        
        # Submit tasks concurrently
        task_ids = []
        for task in tasks:
            task_id = await self.orchestrator.submit_task(task)
            task_ids.append(task_id)
        
        # Poll for completion
        max_retries = 20
        retry_count = 0
        completed_tasks = set()
        
        while retry_count < max_retries and len(completed_tasks) < len(task_ids):
            for task_id in task_ids:
                if task_id in completed_tasks:
                    continue
                    
                status = await self.orchestrator.get_task_status(task_id)
                if status["status"] == "completed":
                    completed_tasks.add(task_id)
            
            retry_count += 1
            await asyncio.sleep(1)
        
        # Collect results
        results = {}
        for task_id in task_ids:
            results[task_id] = await self.orchestrator.get_task_results(task_id)
        
        return {
            "passed": len(completed_tasks) == len(task_ids),
            "total_tasks": len(task_ids),
            "completed_tasks": len(completed_tasks),
            "retry_count": retry_count,
            "results": results
        }

    async def test_error_handling(self):
        """Test error handling and retry mechanism."""
        class FailingPDFService(PDFExtractionService):
            def __init__(self):
                super().__init__()
                self.attempt_count = 0
            
            async def process_document(self, content):
                self.attempt_count += 1
                if self.attempt_count == 1:
                    raise Exception("Simulated first attempt failure")
                return await super().process_document(content)
        
        # Replace PDF service with failing version
        failing_service = FailingPDFService()
        self.service_registry.register_service(failing_service)
        
        # Read sample PDF
        with open("test_data/sample.pdf", "rb") as f:
            pdf_content = base64.b64encode(f.read()).decode()
        
        # Submit task
        task = {
            "task_type": "document_analysis",
            "content": {
                "file_content": pdf_content,
                "analysis_types": ["pdf_extraction"]
            }
        }
        
        task_id = await self.orchestrator.submit_task(task)
        
        # Poll for completion
        max_retries = 3
        retry_count = 0
        final_status = None
        
        while retry_count < max_retries:
            status = await self.orchestrator.get_task_status(task_id)
            if status["status"] == "completed":
                final_status = status
                break
            retry_count += 1
            await asyncio.sleep(1)
        
        # Restore original service
        self.service_registry.register_service(self.pdf_service)
        
        return {
            "passed": final_status is not None and final_status["status"] == "completed",
            "attempts": failing_service.attempt_count,
            "final_status": final_status
        }

    async def test_system_recovery(self):
        """Test system recovery after service crashes."""
        class CrashingPDFService(PDFExtractionService):
            def __init__(self):
                super().__init__()
                self.crash_count = 0
                self.recovery_count = 0
            
            async def process_document(self, content):
                if self.crash_count < 2:
                    self.crash_count += 1
                    raise Exception(f"Simulated crash #{self.crash_count}")
                self.recovery_count += 1
                return await super().process_document(content)
        
        # Replace PDF service with crashing version
        crashing_service = CrashingPDFService()
        self.service_registry.register_service(crashing_service)
        
        # Read sample PDF
        with open("test_data/sample.pdf", "rb") as f:
            pdf_content = base64.b64encode(f.read()).decode()
        
        # Submit task
        task = {
            "task_type": "document_analysis",
            "content": {
                "file_content": pdf_content,
                "analysis_types": ["pdf_extraction"]
            }
        }
        
        task_id = await self.orchestrator.submit_task(task)
        
        # Poll for completion
        max_retries = 5
        retry_count = 0
        status_history = []
        
        while retry_count < max_retries:
            status = await self.orchestrator.get_task_status(task_id)
            status_history.append(status)
            
            if status["status"] == "completed":
                break
                
            retry_count += 1
            await asyncio.sleep(1)
        
        # Restore original service
        self.service_registry.register_service(self.pdf_service)
        
        return {
            "passed": crashing_service.crash_count == 2 and crashing_service.recovery_count > 0,
            "crash_count": crashing_service.crash_count,
            "recovery_count": crashing_service.recovery_count,
            "status_history": status_history
        }

    async def test_full_workflow(self):
        """Test full end-to-end workflow."""
        # Read sample PDF
        with open("test_data/sample.pdf", "rb") as f:
            pdf_content = base64.b64encode(f.read()).decode()
        
        # Upload file
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field("file",
                          pdf_content,
                          filename="sample.pdf",
                          content_type="application/pdf")
            
            async with session.post("http://localhost:8000/api/v1/upload", data=data) as response:
                upload_status = response.status
                upload_response = await response.json()
                
                if upload_status != 200:
                    return {
                        "passed": False,
                        "stage": "upload",
                        "error": upload_response
                    }
                
                file_id = upload_response["file_id"]
        
        # Submit comprehensive analysis task
        task = {
            "task_type": "document_analysis",
            "content": {
                "file_id": file_id,
                "analysis_types": ["pdf_extraction", "sentiment", "summary", "topics"]
            }
        }
        
        task_id = await self.orchestrator.submit_task(task)
        
        # Poll for completion
        max_retries = 30
        retry_count = 0
        
        while retry_count < max_retries:
            status = await self.orchestrator.get_task_status(task_id)
            if status["status"] == "completed":
                break
            retry_count += 1
            await asyncio.sleep(1)
        
        # Get results
        results = await self.orchestrator.get_task_results(task_id)
        
        # Validate results
        validation = {
            "has_text": "text" in results.get("pdf_extraction", {}),
            "has_sentiment": "score" in results.get("sentiment", {}),
            "has_summary": "summary" in results.get("summary", {}),
            "has_topics": isinstance(results.get("topics", []), list)
        }
        
        return {
            "passed": all(validation.values()),
            "file_id": file_id,
            "task_id": task_id,
            "validation": validation,
            "results": results
        }

@pytest.fixture(scope="function")
async def service_registry() -> AsyncGenerator[ServiceRegistry, None]:
    """Create and initialize service registry for testing.
    
    Returns:
        AsyncGenerator[ServiceRegistry, None]: Initialized service registry
    """
    registry = ServiceRegistry()
    
    # Initialize services
    pdf_service = PDFExtractionService()
    sentiment_service = SentimentAnalysisService()
    chatbot_service = ChatbotService()
    rag_service = RAGScraperService()
    recommendation_service = RecommendationService()
    
    # Register services
    registry.register_service("pdf_extraction", pdf_service)
    registry.register_service("sentiment_analysis", sentiment_service)
    registry.register_service("chatbot", chatbot_service)
    registry.register_service("rag_scraper", rag_service)
    registry.register_service("recommendation", recommendation_service)
    
    await registry.initialize()
    yield registry
    await registry.cleanup()

@pytest.fixture(scope="function")
async def orchestrator(service_registry: ServiceRegistry) -> AsyncGenerator[Orchestrator, None]:
    """Create and initialize orchestrator for testing.
    
    Args:
        service_registry: Initialized service registry
        
    Returns:
        AsyncGenerator[Orchestrator, None]: Initialized orchestrator
    """
    orchestrator = Orchestrator(service_registry)
    await orchestrator.initialize()
    yield orchestrator
    await orchestrator.cleanup()

@pytest.mark.asyncio
async def test_health_checks(test_runner: Dict[str, Any]):
    """Test health checks."""
    service_registry = test_runner['service_registry']
    result = await run_health_checks_impl(service_registry)
    assert result["passed"], f"Health checks failed: {result.get('details', {}).get('error')}"

@pytest.mark.asyncio
async def test_invalid_file_upload(test_runner: Dict[str, Any]):
    """Test invalid file upload."""
    service_registry = test_runner['service_registry']
    orchestrator = Orchestrator(service_registry)
    await orchestrator.initialize()
    try:
        result = await run_invalid_file_upload(orchestrator)
        assert result["passed"], f"Invalid file upload test failed: {result.get('details', {}).get('error')}"
    finally:
        await orchestrator.cleanup()

@pytest.mark.asyncio
async def test_task_dependencies(test_runner: Dict[str, Any]):
    """Test task dependency resolution."""
    service_registry = test_runner['service_registry']
    orchestrator = Orchestrator(service_registry)
    await orchestrator.initialize()
    try:
        result = await run_task_dependencies_impl(orchestrator)
        assert result["passed"], f"Task dependencies test failed: {result.get('details', {}).get('error')}"
    finally:
        await orchestrator.cleanup()

@pytest.mark.asyncio
async def test_concurrent_tasks(test_runner: Dict[str, Any]):
    """Test concurrent task processing."""
    service_registry = test_runner['service_registry']
    result = await run_concurrent_tasks_impl(service_registry)
    assert result["passed"], f"Concurrent tasks test failed: {result.get('details', {}).get('error')}"

@pytest.mark.asyncio
async def test_error_handling(test_runner: Dict[str, Any]):
    """Test error handling."""
    service_registry = test_runner['service_registry']
    orchestrator = Orchestrator(service_registry)
    await orchestrator.initialize()
    try:
        result = await run_error_handling(orchestrator)
        assert result["passed"], f"Error handling test failed: {result.get('details', {}).get('error')}"
    finally:
        await orchestrator.cleanup()

@pytest.mark.asyncio
async def test_system_recovery(test_runner: Dict[str, Any]):
    """Test system recovery after failures."""
    service_registry = test_runner['service_registry']
    orchestrator = Orchestrator(service_registry)
    await orchestrator.initialize()
    try:
        result = await run_system_recovery_impl(service_registry, orchestrator)
        assert result["passed"], f"System recovery test failed: {result.get('details', {}).get('error')}"
    finally:
        await orchestrator.cleanup()

@pytest.mark.asyncio
async def test_full_workflow(test_runner: Dict[str, Any]):
    """Test complete end-to-end workflow."""
    service_registry = test_runner['service_registry']
    orchestrator = Orchestrator(service_registry)
    await orchestrator.initialize()
    try:
        result = await run_full_workflow_impl(orchestrator)
        assert result["passed"], f"Full workflow test failed: {result.get('details', {}).get('error')}"
    finally:
        await orchestrator.cleanup()

async def main():
    """Run all tests and generate report."""
    runner = TestRunner()
    
    try:
        # Initialize
        await runner.initialize()

        # Run all tests
        await runner.run_all_tests()

        # Generate report
        report = runner.generate_report()
        print("\nTest Report:")
        print(report)

    finally:
        # Cleanup
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 