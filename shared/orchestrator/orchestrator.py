"""Orchestrator module for coordinating tasks and services."""
from typing import Dict, Any, Optional, List
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from shared.base_service import BaseService
from src.orchestrator.task_decomposer import DynamicTaskDecomposer, TaskDecomposition

@dataclass
class TaskStatus:
    """Status of a task in the orchestrator."""
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    created_at: datetime
    updated_at: datetime
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    subtasks: List[Dict[str, Any]] = field(default_factory=list)

class Orchestrator(BaseService):
    """Main orchestrator service for managing tasks and coordinating services."""
    
    def __init__(self):
        """Initialize the orchestrator."""
        super().__init__("orchestrator")
        self.task_decomposer = DynamicTaskDecomposer()
        self.tasks: Dict[str, TaskStatus] = {}
        self.services: Dict[str, BaseService] = {}
    
    async def submit_task(self, request: Dict[str, Any]) -> str:
        """Submit a new task for processing.
        
        Args:
            request: Dictionary containing task details:
                - task_id: Optional task ID (will be generated if not provided)
                - task_type: Type of task to process
                - content: Task content and parameters
                - context: Optional context information
                
        Returns:
            Task ID for tracking the task.
        """
        task_id = request.get("task_id", str(uuid.uuid4()))
        now = datetime.utcnow()
        
        self.tasks[task_id] = TaskStatus(
            task_id=task_id,
            status="pending",
            created_at=now,
            updated_at=now
        )
        
        # Start task processing in background
        asyncio.create_task(self._process_task(
            task_id=task_id,
            task_type=request["task_type"],
            content=request["content"],
            context=request.get("context")
        ))
        
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a task.
        
        Args:
            task_id: ID of the task to check.
            
        Returns:
            TaskStatus object if found, None otherwise.
        """
        return self.tasks.get(task_id)
    
    async def get_task_results(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the results of a completed task.
        
        Args:
            task_id: ID of the task to get results for.
            
        Returns:
            Dict containing task results if task is completed, None otherwise.
            
        Raises:
            ValueError: If task is not found.
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        if task.status == "completed":
            return {
                "status": task.status,
                "analysis": {
                    "summary": task.result.get("chatbot", {}).get("summary"),
                    "key_points": task.result.get("chatbot", {}).get("key_points", [])
                },
                "extracted_text": task.result.get("pdf_extractor", {}).get("text"),
                "sentiment": task.result.get("sentiment_analyzer", {}).get("sentiment"),
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            }
        elif task.status == "failed":
            return {
                "status": task.status,
                "error": task.error,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            }
        else:
            return {
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            }
    
    async def _process_task(self, task_id: str, task_type: str, content: Dict[str, Any], context: Optional[Dict[str, Any]]) -> None:
        """Process a task by decomposing it and executing subtasks.
        
        Args:
            task_id: ID of the task being processed.
            task_type: Type of task to process.
            content: Task content and parameters.
            context: Optional context information.
        """
        try:
            # Update task status
            task = self.tasks[task_id]
            task.status = "processing"
            task.updated_at = datetime.utcnow()
            
            # Decompose task into subtasks
            decomposition = await self.task_decomposer.decompose(task_type, content, context)
            
            # Process subtasks in order based on dependencies
            results = {}
            for subtask in decomposition.subtasks:
                # Wait for dependencies to complete
                if subtask.dependencies:
                    for dep in subtask.dependencies:
                        if dep not in results:
                            raise ValueError(f"Dependency {dep} not found in results")
                
                # Replace dependency placeholders with actual results
                content = subtask.content.copy()
                for key, value in content.items():
                    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                        dep_name = value[2:-2].split(".")[0]
                        if dep_name in results:
                            content[key] = results[dep_name]
                
                # Execute subtask
                service = self.services.get(subtask.service)
                if not service:
                    raise ValueError(f"Service {subtask.service} not found")
                
                result = await service.process(content)
                results[subtask.service] = result
                
                # Update task status with subtask result
                task.subtasks.append({
                    "service": subtask.service,
                    "status": "completed",
                    "result": result
                })
            
            # Update task status as completed
            task.status = "completed"
            task.result = results
            task.updated_at = datetime.utcnow()
            
        except Exception as e:
            # Update task status as failed
            task = self.tasks[task_id]
            task.status = "failed"
            task.error = str(e)
            task.updated_at = datetime.utcnow()
            raise
    
    def register_service(self, service: BaseService) -> None:
        """Register a service with the orchestrator.
        
        Args:
            service: Service instance to register.
        """
        self.services[service.name] = service
    
    def unregister_service(self, service_name: str) -> None:
        """Unregister a service from the orchestrator.
        
        Args:
            service_name: Name of the service to unregister.
        """
        if service_name in self.services:
            del self.services[service_name]

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
            
        task_type = request["task_type"]
        content = request["content"]
        context = request.get("context")
        
        task_id = await self.submit_task(task_type, content, context)
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Task submitted successfully"
        } 