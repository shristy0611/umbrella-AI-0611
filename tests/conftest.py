"""Common test fixtures for UMBRELLA-AI test suite."""

import os
import pytest
import asyncio
from typing import Generator, Any
from unittest.mock import Mock
import google.generativeai as genai
from shared.gemini import gemini_config

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, Any, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_env() -> Generator[dict, Any, None]:
    """Set up test environment variables."""
    original_env = {}
    test_vars = {
        'GEMINI_API_KEY': 'test_key',
        'GEMINI_API_VERSION': 'v1alpha',
        'GEMINI_MAX_RETRIES': '3',
        'LOG_LEVEL': 'DEBUG'
    }
    
    # Save original environment
    for key in test_vars:
        if key in os.environ:
            original_env[key] = os.environ[key]
    
    # Set test environment
    for key, value in test_vars.items():
        os.environ[key] = value
    
    yield test_vars
    
    # Restore original environment
    for key in test_vars:
        if key in original_env:
            os.environ[key] = original_env[key]
        else:
            del os.environ[key]

@pytest.fixture
def mock_gemini_response() -> Mock:
    """Create a mock Gemini API response."""
    response = Mock()
    response.text = "Mock response text"
    response.candidates = [Mock(content=Mock(text="Mock response text"))]
    response.safety_ratings = [
        Mock(category="HARM_CATEGORY_HARASSMENT", probability="NEGLIGIBLE"),
        Mock(category="HARM_CATEGORY_HATE_SPEECH", probability="NEGLIGIBLE")
    ]
    return response

@pytest.fixture
def mock_gemini_client(mock_gemini_response: Mock) -> Mock:
    """Create a mock Gemini client."""
    client = Mock()
    client.generate_content_async = AsyncMock(return_value=mock_gemini_response)
    return client

@pytest.fixture
def sample_pdf_path() -> str:
    """Path to sample PDF for testing."""
    return os.path.join('tests', 'data', 'documents', 'sample.pdf')

@pytest.fixture
def sample_image_path() -> str:
    """Path to sample image for testing."""
    return os.path.join('tests', 'data', 'images', 'sample.jpg')

@pytest.fixture
def mock_orchestrator_request() -> dict:
    """Sample orchestrator request for testing."""
    return {
        "task_id": "test-123",
        "user_id": "user-456",
        "request_type": "document_analysis",
        "content": {
            "document_url": "https://example.com/doc.pdf",
            "analysis_type": "full",
            "priority": "high"
        }
    }

class AsyncMock(Mock):
    """Mock class that works with async/await."""
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass 