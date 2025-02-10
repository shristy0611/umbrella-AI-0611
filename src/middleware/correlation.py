"""FastAPI middleware for correlation ID handling."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import uuid
from ..utils.logging import set_correlation_id, get_correlation_id

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation IDs in requests."""
    
    def __init__(self, app: ASGIApp, header_name: str = "X-Correlation-ID"):
        """Initialize the middleware.
        
        Args:
            app: The ASGI application
            header_name: Name of the correlation ID header
        """
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and add correlation ID.
        
        Args:
            request: The incoming request
            call_next: The next middleware/application to call
        
        Returns:
            The response from the application
        """
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get(self.header_name)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Set correlation ID in context
        set_correlation_id(correlation_id)
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers[self.header_name] = correlation_id
        
        return response 