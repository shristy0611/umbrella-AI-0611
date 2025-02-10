"""Task decomposition module for the UMBRELLA-AI orchestrator."""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import asyncio

@dataclass
class SubTask:
    """Represents a subtask in the task decomposition."""
    service: str
    content: Dict[str, Any]
    dependencies: Optional[List[str]] = None

@dataclass
class TaskDecomposition:
    """Represents the decomposition of a task into subtasks."""
    subtasks: List[SubTask]
    metadata: Optional[Dict[str, Any]] = None

class DynamicTaskDecomposer:
    """Dynamically decomposes tasks into subtasks based on task type and content."""
    
    def __init__(self, use_mock: bool = False):
        """Initialize the task decomposer.
        
        Args:
            use_mock: Whether to use mock responses for testing.
        """
        self.use_mock = use_mock
        self._workflow_registry = {
            "document_analysis": self._decompose_document_analysis,
            "web_research": self._decompose_web_research
        }
    
    async def decompose(self, task_type: str, content: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskDecomposition:
        """Decompose a task into subtasks.
        
        Args:
            task_type: The type of task to decompose.
            content: The task content and parameters.
            context: Optional context information.
            
        Returns:
            A TaskDecomposition object containing the subtasks.
            
        Raises:
            ValueError: If the task type is not supported.
        """
        if task_type not in self._workflow_registry:
            raise ValueError(f"No fallback workflow available for task type: {task_type}")
        
        decomposition_func = self._workflow_registry[task_type]
        return await decomposition_func(content, context or {})
    
    async def _decompose_document_analysis(self, content: Dict[str, Any], context: Dict[str, Any]) -> TaskDecomposition:
        """Decompose a document analysis task."""
        subtasks = [
            SubTask(
                service="pdf_extractor",
                content={"file": content["file"]},
                dependencies=None
            ),
            SubTask(
                service="sentiment_analyzer",
                content={"text": "{{pdf_extractor.output}}"},
                dependencies=["pdf_extractor"]
            ),
            SubTask(
                service="chatbot",
                content={
                    "text": "{{sentiment_analyzer.output}}",
                    "context": context
                },
                dependencies=["sentiment_analyzer"]
            )
        ]
        return TaskDecomposition(subtasks=subtasks)
    
    async def _decompose_web_research(self, content: Dict[str, Any], context: Dict[str, Any]) -> TaskDecomposition:
        """Decompose a web research task."""
        subtasks = [
            SubTask(
                service="web_scraper",
                content={
                    "url": content["url"],
                    "max_depth": content.get("max_depth", 1),
                    "follow_links": content.get("follow_links", False)
                },
                dependencies=None
            ),
            SubTask(
                service="content_analyzer",
                content={"content": "{{web_scraper.output}}"},
                dependencies=["web_scraper"]
            )
        ]
        return TaskDecomposition(subtasks=subtasks) 