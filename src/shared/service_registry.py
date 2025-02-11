"""Service registry module for managing service instances."""

from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ServiceInfo:
    """Service information."""
    name: str
    instance: Any
    metadata: Dict[str, Any]

class ServiceRegistry:
    """Registry for managing service instances."""
    
    def __init__(self):
        """Initialize service registry."""
        self._services: Dict[str, ServiceInfo] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all registered services."""
        if self._initialized:
            return
            
        # Initialize all services
        for service_info in self._services.values():
            if hasattr(service_info.instance, 'initialize'):
                await service_info.instance.initialize()
        
        self._initialized = True
    
    async def cleanup(self) -> None:
        """Clean up all registered services."""
        # Clean up all services
        for service_info in self._services.values():
            if hasattr(service_info.instance, 'cleanup'):
                await service_info.instance.cleanup()
        
        self._services.clear()
        self._initialized = False
    
    def register_service(
        self,
        name: str,
        instance: Any,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Register a service.
        
        Args:
            name: Service name
            instance: Service instance
            metadata: Optional service metadata
        """
        self._services[name] = ServiceInfo(
            name=name,
            instance=instance,
            metadata=metadata or {}
        )
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get a service by name.
        
        Args:
            name: Service name
            
        Returns:
            Optional[Any]: Service instance if found
        """
        service_info = self._services.get(name)
        return service_info.instance if service_info else None
    
    def get_service_info(self, name: str) -> Optional[ServiceInfo]:
        """Get service information.
        
        Args:
            name: Service name
            
        Returns:
            Optional[ServiceInfo]: Service information if found
        """
        return self._services.get(name)
    
    def list_services(self) -> Dict[str, ServiceInfo]:
        """List all registered services.
        
        Returns:
            Dict[str, ServiceInfo]: Dictionary of service information
        """
        return self._services.copy()
    
    def unregister_service(self, name: str):
        """Unregister a service.
        
        Args:
            name: Service name
        """
        if name in self._services:
            del self._services[name]
    
    def clear(self):
        """Clear all registered services."""
        self._services.clear()
    
    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """Get service metadata.
        
        Args:
            name: Service name
            
        Returns:
            Optional[Dict[str, Any]]: Service metadata if found
        """
        service_info = self._services.get(name)
        return service_info.metadata if service_info else None
    
    def update_metadata(self, name: str, metadata: Dict[str, Any]):
        """Update service metadata.
        
        Args:
            name: Service name
            metadata: New metadata
            
        Raises:
            ValueError: If service not found
        """
        if name not in self._services:
            raise ValueError(f"Service {name} not found")
        
        self._services[name].metadata.update(metadata)
    
    @property
    def services(self) -> Dict[str, Any]:
        """Get all registered services.
        
        Returns:
            Dict[str, Any]: Dictionary of service instances
        """
        return {name: info.instance for name, info in self._services.items()} 