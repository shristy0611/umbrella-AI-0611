"""
Orchestrator service for UmbrellaAI.

This package contains the core orchestration logic for decomposing and executing tasks
across multiple microservices.
"""

from .src.task_decomposer import TaskType, ServiceType, SubTask, DynamicTaskDecomposer
from .src.task_graph import TaskGraph

__version__ = "0.1.0"
__all__ = ["TaskType", "ServiceType", "SubTask", "DynamicTaskDecomposer", "TaskGraph"] 