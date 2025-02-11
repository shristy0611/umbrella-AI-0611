"""Orchestrator module for coordinating tasks and services."""

import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict

from src.shared.service_registry import ServiceRegistry
from src.task_decomposer import DynamicTaskDecomposer, TaskDecomposition
from src.shared.base_service import BaseService

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class TaskStatus:
    """Task status information."""
    task_id: str
    status: str  # pending, processing, completed, failed, cancelled
    created_at: datetime
    updated_at: datetime
    task_type: str
    content: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    progress: float = 0.0
    subtasks: List[Dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    
    def __getitem__(self, key):
        """Support dictionary-like access."""
        return asdict(self)[key]
    
    def get(self, key, default=None):
        """Dictionary-like get method."""
        return asdict(self).get(key, default)

class Orchestrator(BaseService):
    """Main orchestrator service for managing tasks and coordinating services."""
    
    def __init__(self):
        """Initialize the orchestrator."""
        super().__init__("orchestrator")
        self.task_decomposer = None  # Will be set from service registry
        self.tasks: Dict[str, TaskStatus] = {}
        self.services: Dict[str, BaseService] = {}
        self.service_registry = ServiceRegistry()
        self._locks: Dict[str, asyncio.Lock] = {}
        
    async def initialize(self) -> None:
        """Initialize the orchestrator."""
        logging.info("Initializing orchestrator...")

        # Initialize and register task decomposer
        self.task_decomposer = DynamicTaskDecomposer(use_mock=True)
        await self.task_decomposer.initialize()
        self.service_registry.register_service("task_decomposer", self.task_decomposer)

        logging.info("Orchestrator initialized successfully")
        
    async def cleanup(self) -> None:
        """Clean up orchestrator resources."""
        # Clean up services
        for service in self.services.values():
            await service.cleanup()
            
        # Clean up task decomposer
        if self.task_decomposer:
            await self.task_decomposer.cleanup()
            
        # Clean up service registry
        if self.service_registry:
            await self.service_registry.cleanup()
            
        self.tasks.clear()
        self._locks.clear()
        
        await super().cleanup()
    
    async def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request through the orchestrator.
        
        Args:
            request: Dictionary containing task details:
                - task_type: Type of task to process
                - content: Task content and parameters
                - context: Optional context information
                
        Returns:
            Dictionary containing task ID and initial status
            
        Raises:
            ValueError: If required fields are missing
        """
        if "task_type" not in request:
            raise ValueError("task_type is required")
        if "content" not in request:
            raise ValueError("content is required")
            
        task_id = await self.submit_task(request)
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Task submitted successfully"
        }
    
    async def submit_task(self, request: Dict[str, Any]) -> str:
        """Submit a new task.
        
        Args:
            request: Task request containing type, content, and context
            
        Returns:
            str: Task ID
        """
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = TaskStatus(
            task_id=task_id,
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            task_type=request["task_type"],
            content=request["content"],
            context=request.get("context")
        )
        self._locks[task_id] = asyncio.Lock()
        return task_id
    
    async def get_task_status(self, task_id: str) -> TaskStatus:
        """Get status of a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            TaskStatus: Task status information
            
        Raises:
            ValueError: If task not found
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        return self.tasks[task_id]
    
    async def get_task_results(self, task_id: str) -> Dict[str, Any]:
        """Get results of a completed task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Dict[str, Any]: Task results
            
        Raises:
            ValueError: If task not found or not completed
        """
        status = await self.get_task_status(task_id)
        if status.status != "completed":
            raise ValueError(f"Task {task_id} not completed")
        return status.result or {}
    
    async def process_task(self, task_id: str) -> Dict[str, Any]:
        """Process a submitted task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Dict[str, Any]: Processing results
        """
        async with self._locks[task_id]:
            try:
                # Get task details
                task = self.tasks[task_id]
                
                # Update status
                task.status = "processing"
                task.started_at = datetime.now()
                task.updated_at = datetime.now()
                
                # Ensure task decomposer is available
                if not self.task_decomposer:
                    self.task_decomposer = self.service_registry.get_service("task_decomposer")
                    if not self.task_decomposer:
                        raise ValueError("Task decomposer service not available")
                
                # Decompose task into subtasks
                decomposition = await self.task_decomposer.decompose(
                    task.task_type,
                    task.content,
                    task.context
                )
                
                # Process subtasks
                results = {}
                total_subtasks = len(decomposition.subtasks)
                
                for i, subtask in enumerate(decomposition.subtasks):
                    # Check dependencies
                    for dep in subtask.get("dependencies", []):
                        if dep not in results:
                            raise ValueError(f"Dependency {dep} not satisfied")
                    
                    # Replace dependency placeholders in data
                    data = subtask.get("data", {}).copy()
                    for key, value in data.items():
                        if isinstance(value, str) and value.startswith("$"):
                            parts = value[1:].split(".")
                            dep_result = results[parts[0]]
                            for part in parts[1:]:
                                if isinstance(dep_result, dict):
                                    dep_result = dep_result.get(part)
                                else:
                                    raise ValueError(f"Cannot resolve dependency {value}")
                            data[key] = dep_result
                    
                    # Get service
                    service_name = subtask.get("service")
                    if not service_name:
                        raise ValueError("Service name not specified in subtask")
                    
                    service = self.service_registry.get_service(service_name)
                    if not service:
                        raise ValueError(f"Service {service_name} not found")
                    
                    # Process subtask with retries
                    max_retries = subtask.get("max_retries", 3)
                    retry_delay = subtask.get("retry_delay", 1)
                    last_error = None
                    
                    for retry in range(max_retries):
                        try:
                            result = await service.process({
                                "action": subtask.get("action", "process"),
                                **data
                            })
                            results[service_name] = result
                            task.subtasks.append({
                                "service": service_name,
                                "status": "completed",
                                "result": result
                            })
                            break
                        except Exception as e:
                            last_error = str(e)
                            if retry < max_retries - 1:
                                await asyncio.sleep(retry_delay)
                                continue
                            raise ValueError(f"Service {service_name} failed after {max_retries} retries: {last_error}")
                    
                    # Update progress
                    task.progress = (i + 1) / total_subtasks
                    task.updated_at = datetime.now()
                
                # Update task status
                task.status = "completed"
                task.completed_at = datetime.now()
                task.result = results
                task.updated_at = datetime.now()
                
                return results
                
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                task.updated_at = datetime.now()
                raise
    
    async def cancel_task(self, task_id: str):
        """Cancel a task.
        
        Args:
            task_id: Task ID
            
        Raises:
            ValueError: If task not found
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        async with self._locks[task_id]:
            self.tasks[task_id].status = "cancelled"
            self.tasks[task_id].completed_at = datetime.now()
    
    def _cleanup_task(self, task_id: str):
        """Clean up task resources.
        
        Args:
            task_id: Task ID
        """
        if task_id in self._locks:
            del self._locks[task_id] 