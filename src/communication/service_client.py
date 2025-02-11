"""Service client for making HTTP requests to other services."""

import httpx
import logging
import asyncio
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class ServiceClient:
    """HTTP client for making requests to services."""
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        """Initialize the service client.
        
        Args:
            base_url: Base URL of the service
            timeout: Timeout for requests
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
    
    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        data: Any = None,
        json: Any = None,
        headers: Optional[Dict[str, str]] = None,
        correlation_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the service."""
        url = f"{self.base_url}{endpoint}"
        timeout = timeout or self.timeout
        
        default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if correlation_id:
            default_headers["X-Correlation-ID"] = correlation_id
            
        headers = {**default_headers, **(headers or {})}
        
        async with httpx.AsyncClient() as client:
            for attempt in range(3):
                try:
                    response = await client.request(
                        method,
                        url,
                        json=json if json is not None else data,
                        headers=headers,
                        timeout=timeout
                    )
                    response.raise_for_status()
                    return response.json()
                except Exception as e:
                    if attempt == 2:  # Last attempt
                        self.logger.error(f"Request to {self.base_url} failed after 3 retries: {str(e)}")
                        raise
                    self.logger.warning(f"Request to {self.base_url} failed (attempt {attempt + 1}/3). Retrying in {2**attempt}s...")
                    await asyncio.sleep(2**attempt)
    
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a GET request."""
        return await self.request("GET", endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a POST request."""
        return await self.request("POST", endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a PUT request."""
        return await self.request("PUT", endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a DELETE request."""
        return await self.request("DELETE", endpoint, **kwargs) 