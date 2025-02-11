"""Service registry for UMBRELLA-AI."""

import logging
from typing import Dict, Optional, Type, Any
from shared.base_service import BaseService

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Registry for managing service instances."""

    _instance = None
    _services: Dict[str, BaseService] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceRegistry, cls).__new__(cls)
        return cls._instance

    def register(self, service_name: str, service: BaseService) -> None:
        """Register a service.

        Args:
            service_name: Name of the service
            service: Service instance
        """
        self._services[service_name] = service
        logger.info(f"Registered service: {service_name}")

    def get_service(self, service_name: str) -> Optional[BaseService]:
        """Get a service by name.

        Args:
            service_name: Name of the service

        Returns:
            Optional[BaseService]: Service if found
        """
        service = self._services.get(service_name)
        if not service:
            logger.warning(f"Service not found: {service_name}")
        return service

    def unregister(self, service_name: str) -> None:
        """Unregister a service.

        Args:
            service_name: Name of the service
        """
        if service_name in self._services:
            del self._services[service_name]
            logger.info(f"Unregistered service: {service_name}")

    def list_services(self) -> Dict[str, str]:
        """List all registered services.

        Returns:
            Dict[str, str]: Map of service names to their types
        """
        return {
            name: type(service).__name__ for name, service in self._services.items()
        }

    def register_service(self, name: str, service: Any):
        self._services[name] = service

    def get_service_by_name(self, name: str) -> Any:
        service = self._services.get(name)
        if not service:
            raise ValueError(f"Service {name} not registered")
        return service
