"""Test invalid file type handling."""

import asyncio
import base64
import logging
from pathlib import Path
import aiohttp
from src.app import app
from fastapi.testclient import TestClient
import time

logger = logging.getLogger(__name__)

async def test_invalid_file_upload(test_runner):
    """Test invalid file type upload handling.
    
    Args:
        test_runner: Test runner fixture
    
    Returns:
        dict: Test results
    """
    start_time = time.time()
    try:
        # Create test client
        client = TestClient(app)

        # Create a temporary text file
        test_file = Path("test_data/invalid.exe")
        test_file.write_text("This is not a PDF file")

        try:
            # Try to upload invalid file
            with open(test_file, "rb") as f:
                response = client.post(
                    "/api/v1/upload",
                    files={"file": ("test.exe", f, "application/octet-stream")}
                )

            # Validate response
            passed = (
                response.status_code == 400 and
                "Invalid file type" in response.json()["detail"]
            )

            return {
                "passed": passed,
                "duration": time.time() - start_time,
                "details": {
                    "status_code": response.status_code,
                    "response": response.json(),
                    "error": None if passed else "Invalid response for invalid file"
                }
            }

        finally:
            # Cleanup
            test_file.unlink()

    except Exception as e:
        return {
            "passed": False,
            "duration": time.time() - start_time,
            "details": {"error": str(e)}
        } 