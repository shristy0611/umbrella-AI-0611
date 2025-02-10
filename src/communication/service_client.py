"""HTTP client for service-to-service communication."""

import httpx
import logging
from typing import Any, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class ServiceClient:
    """Client for making HTTP requests to other services."""
    
    def __init__(self, base_url: str, service_name: str, timeout: int = 30):
        """Initialize the service client.
        
        Args:
            base_url: Base URL of the service
            service_name: Name of the service
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.service_name = service_name
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def request(
        self,
        method: str,
        endpoint: str,
        correlation_id: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the service.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            correlation_id: Correlation ID for request tracing
            data: Request body data
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Response data as dictionary
            
        Raises:
            httpx.HTTPError: If the request fails
        """
        # Prepare headers
        request_headers = {
            "X-Correlation-ID": correlation_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
            **(headers or {})
        }
        
        # Build full URL
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            # Make request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers
                )
                
                # Raise for status
                response.raise_for_status()
                
                logger.info(
                    f"Request to {self.service_name} successful",
                    extra={
                        "service": self.service_name,
                        "method": method,
                        "url": url,
                        "correlation_id": correlation_id,
                        "status_code": response.status_code
                    }
                )
                
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(
                f"Request to {self.service_name} failed: {str(e)}",
                extra={
                    "service": self.service_name,
                    "method": method,
                    "url": url,
                    "correlation_id": correlation_id,
                    "error": str(e)
                }
            )
            raise 