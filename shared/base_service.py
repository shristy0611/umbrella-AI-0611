"""Base service class for UMBRELLA-AI services."""
from typing import Dict, Any, Optional
import abc
import logging
from fastapi import FastAPI, Request
from .logging_utils import setup_logger, with_correlation_id
from .middleware import CorrelationIdMiddleware

logger = logging.getLogger(__name__)

class BaseService(abc.ABC):
    """Abstract base class for all services in UMBRELLA-AI."""
    
    def __init__(self, name: str):
        """Initialize the service.
        
        Args:
            name: Name of the service.
        """
        self.name = name
        self._logger = logger.getChild(name)
        self._logger.info(f"Initializing service: {name}")
        self.app = FastAPI(title=name)
        
        # Add correlation ID middleware
        self.app.add_middleware(CorrelationIdMiddleware)
        
        # Add startup and shutdown event handlers
        self.app.add_event_handler("startup", self.startup_event)
        self.app.add_event_handler("shutdown", self.shutdown_event)
    
    @abc.abstractmethod
    async def process(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request.
        
        Args:
            content: Request content and parameters.
            
        Returns:
            Dict containing the processing results.
            
        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Service must implement process method")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the service.
        
        Returns:
            Dict containing health status information.
        """
        return {
            "status": "healthy",
            "service": {
                "name": self.name,
                "status": "healthy"
            }
        }
    
    async def shutdown(self) -> None:
        """Clean up resources before shutting down."""
        self._logger.info(f"Shutting down service: {self.name}")
    
    def __str__(self) -> str:
        """Get string representation of the service.
        
        Returns:
            String representation.
        """
        return f"{self.__class__.__name__}(name={self.name})"
    
    async def startup_event(self):
        """Handle service startup."""
        self._logger.info("Starting %s service", self.name)
    
    async def shutdown_event(self):
        """Handle service shutdown."""
        self.logger.info("Shutting down %s service", self.service_name)
    
    @with_correlation_id
    async def process_request(self, request_data: Dict[str, Any], correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a service request with correlation ID support.
        
        Args:
            request_data: The request data to process
            correlation_id: Optional correlation ID for request tracing
            
        Returns:
            The processed response data
            
        This method should be overridden by service implementations.
        """
        self.logger.debug("Processing request: %s", request_data)
        raise NotImplementedError("Service must implement process_request method")
    
    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        return self.app 