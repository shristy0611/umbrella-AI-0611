"""Base service class for all UMBRELLA-AI services."""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class BaseService(ABC):
    """Base class for all services."""
    
    def __init__(self, service_name: str):
        """Initialize base service.
        
        Args:
            service_name: Name of the service
        """
        self.service_name = service_name
        self.started_at = datetime.now()
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the service. Must be called before using the service.
        
        This method should be overridden by subclasses to perform any necessary
        initialization like setting up connections, loading models, etc.
        """
        self._initialized = True
        
    async def cleanup(self) -> None:
        """Clean up service resources.
        
        This method should be overridden by subclasses to perform any necessary
        cleanup like closing connections, freeing resources, etc.
        """
        self._initialized = False
    
    @abstractmethod
    async def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request.
        
        Args:
            request: Request data
            
        Returns:
            Dict[str, Any]: Processing results
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        if not self._initialized:
            raise RuntimeError(f"Service {self.service_name} not initialized")
        raise NotImplementedError
    
    async def validate_request(self, request: Dict[str, Any]) -> bool:
        """Validate a request.
        
        Args:
            request: Request to validate
            
        Returns:
            bool: True if request is valid
        """
        return True
    
    async def preprocess(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess a request before processing.
        
        Args:
            request: Request to preprocess
            
        Returns:
            Dict[str, Any]: Preprocessed request
        """
        return request
    
    async def postprocess(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Postprocess results after processing.
        
        Args:
            result: Results to postprocess
            
        Returns:
            Dict[str, Any]: Postprocessed results
        """
        return result
    
    async def handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle processing error.
        
        Args:
            error: Error that occurred
            
        Returns:
            Dict[str, Any]: Error response
        """
        return {
            "status": "error",
            "error": str(error),
            "service": self.service_name,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health.
        
        Returns:
            Dict[str, Any]: Health status
        """
        return {
            "status": "healthy",
            "service": self.service_name,
            "uptime": (datetime.now() - self.started_at).total_seconds(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def __call__(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request with validation and error handling.
        
        Args:
            request: Request to process
            
        Returns:
            Dict[str, Any]: Processing results
        """
        async with self._lock:
            try:
                # Validate request
                if not await self.validate_request(request):
                    raise ValueError("Invalid request")
                
                # Preprocess
                preprocessed = await self.preprocess(request)
                
                # Process
                result = await self.process(preprocessed)
                
                # Postprocess
                postprocessed = await self.postprocess(result)
                
                return {
                    "status": "success",
                    "result": postprocessed,
                    "service": self.service_name,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                return await self.handle_error(e)
        
    def get_service(self, service_name: str) -> Optional['BaseService']:
        """Get a service by name.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Optional[BaseService]: Service if found
        """
        # This will be implemented by the service registry
        # For now, return None
        return None
        
    def _log_error(self, message: str, error: Optional[Exception] = None) -> None:
        """Log an error message.
        
        Args:
            message: Error message
            error: Optional exception
        """
        if error:
            self._logger.error(f"{message}: {str(error)}")
        else:
            self._logger.error(message)
            
    def _log_info(self, message: str) -> None:
        """Log an info message.
        
        Args:
            message: Info message
        """
        self._logger.info(message)
        
    def _log_debug(self, message: str) -> None:
        """Log a debug message.
        
        Args:
            message: Debug message
        """
        self._logger.debug(message)
        
    def _log_warning(self, message: str) -> None:
        """Log a warning message.
        
        Args:
            message: Warning message
        """
        self._logger.warning(message) 