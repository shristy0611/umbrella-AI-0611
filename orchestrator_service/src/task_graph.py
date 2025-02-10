from typing import Dict, List, Set, Any, Optional
import asyncio
import httpx
import logging
from datetime import datetime
from .task_decomposer import SubTask, ServiceType
from enum import Enum

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Enum representing the status of a task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskGraph:
    """Manages execution of interdependent tasks."""
    
    def __init__(self):
        """Initialize a new task graph."""
        self.tasks: Dict[str, SubTask] = {}
        self.results: Dict[str, Any] = {}
        self.completed: Set[str] = set()
        self.failed: Set[str] = set()
        self.in_progress: Set[str] = set()
    
    def add_task(self, task_id: str, task: SubTask):
        """Add a task to the graph.
        
        Args:
            task_id: Unique identifier for the task
            task: The task to add
        """
        self.tasks[task_id] = task
    
    async def execute(self, correlation_id: str) -> Dict[str, Any]:
        """Execute all tasks in the graph."""
        try:
            async with httpx.AsyncClient() as client:
                tasks = [
                    self._execute_task(task_id, task, client, correlation_id)
                    for task_id, task in self.tasks.items()
                ]
                await asyncio.gather(*tasks)
                return {
                    "status": "completed",
                    "results": self.results,
                    "tasks": self.tasks
                }
        except Exception as e:
            logger.error(f"Error executing task graph: {str(e)}", exc_info=True)
            raise Exception(f"Some tasks failed: {str(e)}")
    
    def _get_ready_tasks(self) -> Set[str]:
        """Get tasks whose dependencies are satisfied and not yet started."""
        ready = set()
        for task_id, task in self.tasks.items():
            if task_id not in self.completed and task_id not in self.failed and task_id not in self.in_progress:
                if not task.dependencies or all(dep in self.completed for dep in task.dependencies):
                    ready.add(task_id)
        return ready
    
    async def _execute_task(self, task_id: str, task: SubTask, client: httpx.AsyncClient, correlation_id: str):
        """Execute a single task and store its result."""
        self.in_progress.add(task_id)
        try:
            # Resolve any dependencies in the task data
            resolved_data = self._resolve_dependencies(task.data)
            
            # Prepare request
            service_url = self._get_service_url(task.service)
            headers = {"X-Correlation-ID": correlation_id}
            
            # Execute request
            response = await client.post(
                f"{service_url}/{task.action}",
                json=resolved_data,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = await response.json()
            
            # Store result and mark task as completed
            self.results[task_id] = result
            self.completed.add(task_id)
            self.in_progress.remove(task_id)
            return result
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}", exc_info=True)
            self.failed.add(task_id)
            self.in_progress.remove(task_id)
            raise
    
    def _resolve_dependencies(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve any dependency references in the task data."""
        resolved = {}
        for key, value in data.items():
            if isinstance(value, str) and value.startswith("$result."):
                # Parse reference like "$result.task_id.field"
                parts = value[8:].split(".")  # Remove "$result." prefix
                if len(parts) != 2:
                    raise ValueError(f"Invalid result reference: {value}")
                task_id, field = parts
                if task_id not in self.results:
                    raise ValueError(f"Referenced task {task_id} not completed")
                resolved[key] = self.results[task_id].get(field)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_dependencies(value)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_dependencies(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                resolved[key] = value
        return resolved
    
    def _get_service_url(self, service: ServiceType) -> str:
        """Get the URL for a service from environment variables."""
        import os
        
        service_env_map = {
            ServiceType.PDF_EXTRACTION: "PDF_SERVICE_URL",
            ServiceType.SENTIMENT: "SENTIMENT_SERVICE_URL",
            ServiceType.CHATBOT: "CHATBOT_SERVICE_URL",
            ServiceType.RAG_SCRAPER: "SCRAPER_SERVICE_URL",
            ServiceType.VECTOR_DB: "VECTOR_DB_URL"
        }
        
        env_var = service_env_map.get(service)
        if not env_var:
            raise ValueError(f"Unknown service: {service}")
            
        url = os.getenv(env_var)
        if not url:
            raise ValueError(f"Missing environment variable: {env_var}")
            
        return url 