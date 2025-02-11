"""Service registry for managing service instances."""

import logging
from typing import Dict, Any, Optional
from src.shared.base_service import BaseService

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """Registry for managing service instances."""
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super(ServiceRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize service registry."""
        if not self._initialized:
            self._services: Dict[str, BaseService] = {}
            self._initialized = True
    
    async def initialize(self) -> None:
        """Initialize all registered services."""
        for service in self._services.values():
            await service.initialize()
    
    def register_service(self, service: BaseService) -> None:
        """Register a service.
        
        Args:
            service: Service to register
        """
        self._services[service.service_name] = service
        logger.info(f"Registered service: {service.service_name}")
    
    def get_service(self, service_name: str) -> Optional[BaseService]:
        """Get a service by name.
        
        Args:
            service_name: Name of service to get
            
        Returns:
            Optional[BaseService]: Service instance if found
        """
        return self._services.get(service_name)
    
    def list_services(self) -> Dict[str, BaseService]:
        """Get all registered services.
        
        Returns:
            Dict[str, BaseService]: Map of service names to instances
        """
        return self._services.copy()
    
    async def cleanup(self) -> None:
        """Clean up all registered services."""
        for service in self._services.values():
            await service.cleanup()
        self._services.clear()
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of all services.
        
        Returns:
            Dict[str, Any]: Health status of all services
        """
        status = {}
        for name, service in self._services.items():
            status[name] = {
                "initialized": service.is_initialized(),
                "healthy": service.health_check()["status"] == "healthy"
            }
        return {
            "status": "healthy" if all(s["healthy"] for s in status.values()) else "unhealthy",
            "services": status
        } 