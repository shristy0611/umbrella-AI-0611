"""Test health check and monitoring."""

import asyncio
import logging
import time
import aiohttp
from src.app import app
from fastapi.testclient import TestClient
import pytest
from tests.e2e.helpers import run_health_checks_impl

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_health_checks(test_runner):
    """Test health check endpoints.
    
    Args:
        test_runner: Test runner fixture
    
    Returns:
        dict: Test results
    """
    try:
        # Get service registry from test runner
        service_registry = test_runner.get('service_registry')
        if not service_registry:
            return {
                "passed": False,
                "details": {"error": "Service registry not found in test runner"}
            }
            
        # Run health checks implementation
        return await run_health_checks_impl(service_registry)
        
    except Exception as e:
        logger.error(f"Health check test failed: {str(e)}")
        return {
            "passed": False,
            "details": {"error": str(e)}
        } 