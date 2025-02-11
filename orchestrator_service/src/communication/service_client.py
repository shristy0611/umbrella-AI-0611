"""
Service client for making HTTP requests to other services.
"""
import httpx
import logging
from typing import Any, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class ServiceClient:
    """
    Client for making HTTP requests to other services with retry logic.
    """
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to a service with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: Service endpoint
            data: Request data (for POST/PUT)
            correlation_id: Request correlation ID
            timeout: Request timeout in seconds
            
        Returns:
            Response data as dictionary
            
        Raises:
            httpx.HTTPError: If the request fails after retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    url,
                    json=data,
                    headers=headers,
                    timeout=timeout
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling {url}: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Error calling {url}: {str(e)}")
            raise httpx.HTTPError(f"Request failed: {str(e)}")
            
    async def get(self, *args, **kwargs) -> Dict[str, Any]:
        """Make a GET request."""
        return await self.request("GET", *args, **kwargs)
        
    async def post(self, *args, **kwargs) -> Dict[str, Any]:
        """Make a POST request."""
        return await self.request("POST", *args, **kwargs)
        
    async def put(self, *args, **kwargs) -> Dict[str, Any]:
        """Make a PUT request."""
        return await self.request("PUT", *args, **kwargs)
        
    async def delete(self, *args, **kwargs) -> Dict[str, Any]:
        """Make a DELETE request."""
        return await self.request("DELETE", *args, **kwargs) 