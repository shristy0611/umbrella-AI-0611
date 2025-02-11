"""Pytest configuration for end-to-end tests."""

import pytest
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any
from src.shared.logging_config import setup_logging
from src.services.service_registry import ServiceRegistry
from src.orchestrator import Orchestrator
from src.services.pdf_extraction import PDFExtractionService
from src.services.sentiment_analysis import SentimentAnalysisService
from src.services.chatbot import ChatbotService
from src.services.rag_scraper import RAGScraperService
from src.services.recommendation.service import RecommendationService

# Configure logging for tests
setup_logging("e2e_tests", log_level="DEBUG", log_file="logs/e2e_tests.log")
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def event_loop(request):
    """Create an instance of the default event loop for the session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
async def setup_teardown():
    """Setup and teardown for each test."""
    # Setup
    logger.info("Setting up test environment")
    yield
    # Teardown
    logger.info("Cleaning up test environment")

@pytest.fixture(scope="function")
async def service_registry() -> AsyncGenerator[ServiceRegistry, None]:
    """Create and initialize service registry for testing.

    Returns:
        AsyncGenerator[ServiceRegistry, None]: Initialized service registry
    """
    registry = ServiceRegistry()
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

@pytest.fixture(scope="function")
async def test_runner(service_registry: ServiceRegistry) -> AsyncGenerator[Dict[str, Any], None]:
    """Create a test runner instance with initialized services.

    Args:
        service_registry: Service registry fixture

    Returns:
        Dict[str, Any]: Test runner with initialized services
    """
    # Initialize services
    services = {
        'pdf_extraction': PDFExtractionService(),
        'document_analysis': PDFExtractionService(),
        'sentiment_analysis': SentimentAnalysisService(),
        'chatbot': ChatbotService(),
        'rag_scraper': RAGScraperService(),
        'recommendation': RecommendationService()
    }
    
    try:
        # Initialize each service
        for name, service in services.items():
            await service.initialize()
            service_registry.register_service(name, service)
            
        # Create test runner dictionary with both service names
        runner = {
            'service_registry': service_registry,
            'pdf_service': services['pdf_extraction'],
            'document_analysis_service': services['document_analysis'],
            'sentiment_service': services['sentiment_analysis'],
            'chatbot_service': services['chatbot'],
            'rag_scraper_service': services['rag_scraper'],
            'recommendation_service': services['recommendation']
        }
        
        yield runner
        
    finally:
        # Cleanup services
        for service in services.values():
            try:
                await service.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up service: {str(e)}")

def pytest_configure(config):
    """Configure pytest for the test session."""
    config.addinivalue_line(
        "markers",
        "pipeline: mark test as a pipeline test"
    )

def pytest_collection_modifyitems(items):
    """Modify test items in-place to ensure proper test ordering."""
    # Add pipeline marker to pipeline tests
    for item in items:
        if "pipeline" in item.nodeid:
            item.add_marker(pytest.mark.pipeline)
            
    # Ensure pipeline tests run last
    items.sort(key=lambda x: 1 if "pipeline" in x.nodeid else 0) 