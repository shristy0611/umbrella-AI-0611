"""
Orchestrator service for UmbrellaAI.

This package contains the core orchestration logic for decomposing and executing tasks
across multiple microservices.
"""

from .task_decomposer import TaskType, ServiceType, SubTask, DynamicTaskDecomposer
from .task_graph import TaskGraph

__version__ = "0.1.0"
__all__ = ["TaskType", "ServiceType", "SubTask", "DynamicTaskDecomposer", "TaskGraph"]
