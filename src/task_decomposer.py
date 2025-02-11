"""Task decomposition module for UMBRELLA-AI."""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid
import os

logger = logging.getLogger(__name__)

class TaskType(Enum):
    """Supported task types."""
    DOCUMENT_ANALYSIS = "document_analysis"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    CHAT = "chat"
    WEB_RESEARCH = "web_research"
    MULTI_STAGE_ANALYSIS = "multi_stage_analysis"

TASK_TYPES = {
    TaskType.DOCUMENT_ANALYSIS.value,
    TaskType.SENTIMENT_ANALYSIS.value,
    TaskType.CHAT.value,
    TaskType.WEB_RESEARCH.value,
    TaskType.MULTI_STAGE_ANALYSIS.value
}

@dataclass
class SubTask:
    """Represents a decomposed subtask."""
    service: str
    action: str
    data: Dict[str, Any]
    priority: int = 0
    dependencies: List[str] = None

@dataclass
class TaskDecomposition:
    """Task decomposition information."""
    task_type: str
    subtasks: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def tasks(self) -> List[Dict[str, Any]]:
        """Alias for subtasks to maintain backward compatibility."""
        return self.subtasks

    def add_subtask(self, subtask: Dict[str, Any]) -> None:
        """Add a subtask to the decomposition."""
        self.subtasks.append(subtask)

    def get_metadata(self) -> Dict[str, Any]:
        """Get the task metadata."""
        return self.metadata

class DynamicTaskDecomposer:
    """Dynamic task decomposer that breaks down tasks based on their type."""
    
    def __init__(self, use_mock: bool = False):
        """Initialize task decomposer.
        
        Args:
            use_mock: Whether to use mock responses for testing
        """
        self.use_mock = use_mock
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initialized DynamicTaskDecomposer with use_mock={use_mock}")
        self._initialized = False
        self._workflows = {}
        self.mock_responses = {}
        
    async def initialize(self) -> None:
        """Initialize the task decomposer."""
        if self._initialized:
            return
            
        self._initialized = True
        logger.info(f"Initialized DynamicTaskDecomposer with use_mock={self.use_mock}")
        
        # Workflow setup
        self._workflows = {
            TaskType.DOCUMENT_ANALYSIS: self._decompose_document_analysis,
            TaskType.SENTIMENT_ANALYSIS: self._decompose_sentiment_analysis,
            TaskType.CHAT: self._decompose_chat,
            TaskType.WEB_RESEARCH: self._decompose_web_research,
            TaskType.MULTI_STAGE_ANALYSIS: self._decompose_multi_stage_analysis
        }
        
        if self.use_mock:
            self._setup_mock_responses()
            
    async def cleanup(self) -> None:
        """Clean up task decomposer resources."""
        self._workflows.clear()
        self.mock_responses.clear()
        self._initialized = False
        
    def _setup_mock_responses(self):
        """Set up mock responses for testing."""
        self.mock_responses = {
            "document_analysis": TaskDecomposition(
                task_type="document_analysis",
                subtasks=[
                    {"name": "pdf_extraction", "service": "pdf_extraction", "data": {"file_id": "mock_file_id", "options": {"extract_text": True, "extract_metadata": True}}},
                    {"name": "sentiment_analysis", "service": "sentiment_analysis", "data": {"text": "This is a mock sentiment analysis", "options": {"granularity": "document"}}},
                ],
                metadata={
                    "file_id": "mock_file_id",
                    "analysis_types": ["text_extraction", "sentiment_analysis"]
                }
            ),
            "web_research": TaskDecomposition(
                task_type="web_research",
                subtasks=[
                    {"type": "scrape_content", "service": "rag_scraper", "input": {"url": "https://example.com", "max_depth": 2}},
                    {"type": "extract_info", "service": "chatbot", "input": {"content": "$scrape_content.output"}},
                ],
                metadata={"depth": 2}
            ),
            "chat_with_context": TaskDecomposition(
                task_type="chat_with_context",
                subtasks=[
                    {"type": "search_context", "service": "vector_db", "params": {"query": "Hello", "limit": 5}},
                    {"type": "generate_response", "service": "chatbot", "params": {"message": "Hello", "session_id": "test-session"}, "depends_on": ["vector_db"]}
                ],
                metadata={"session_id": "test-session"}
            )
        }
    
    async def decompose(
        self,
        task_type: str,
        content: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> TaskDecomposition:
        """Decompose a task into subtasks.
        
        Args:
            task_type: Type of task to decompose
            content: Task content
            context: Additional context
            
        Returns:
            TaskDecomposition: Decomposed task information
            
        Raises:
            ValueError: If task type is not supported
        """
        if not self._initialized:
            raise RuntimeError("Task decomposer not initialized")
        
        if task_type not in TASK_TYPES:
            raise ValueError(f"Unsupported task type: {task_type}")
            
        if self.use_mock:
            return self.mock_responses.get(task_type, self._default_mock_response(task_type))
            
        return await self._workflows[TaskType(task_type)](content, context)
    
    async def _decompose_document_analysis(
        self,
        content: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> TaskDecomposition:
        """Decompose a document analysis task.
        
        Args:
            content: Task content
            context: Additional context
            
        Returns:
            TaskDecomposition: Decomposed task information
        """
        if "file_id" not in content:
            raise ValueError("file_id is required for document analysis")
        
        analysis_types = content.get("analysis_types", ["text_extraction"])
        subtasks = []
        
        # Add PDF extraction subtask
        subtasks.append({
            "name": "pdf_extraction",
            "service": "pdf_extraction",
            "data": {
                "file_id": content["file_id"],
                "options": {
                    "extract_text": True,
                    "extract_metadata": True
                }
            },
            "priority": 1,
            "dependencies": [],
            "max_retries": 3,
            "retry_delay": 1
        })
        
        # Add sentiment analysis if requested
        if "sentiment_analysis" in analysis_types:
            subtasks.append({
                "name": "sentiment_analysis",
                "service": "sentiment_analysis",
                "data": {
                    "text": "$pdf_extraction.text",
                    "options": {
                        "granularity": "document"
                    }
                },
                "priority": 2,
                "dependencies": ["pdf_extraction"],
                "max_retries": 2,
                "retry_delay": 1
            })
        
        return TaskDecomposition(
            task_type="document_analysis",
            subtasks=subtasks,
            metadata={
                "file_id": content["file_id"],
                "analysis_types": analysis_types
            }
        )
    
    async def _decompose_sentiment_analysis(
        self,
        content: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> TaskDecomposition:
        """Decompose a sentiment analysis task.
        
        Args:
            content: Task content
            context: Additional context
            
        Returns:
            TaskDecomposition: Decomposed task information
        """
        if "text" not in content:
            raise ValueError("text is required for sentiment analysis")
        
        return TaskDecomposition(
            task_type="sentiment_analysis",
            subtasks=[{
                "name": "sentiment_analysis",
                "service": "sentiment_analysis",
                "data": {
                    "text": content["text"],
                    "options": content.get("options", {})
                },
                "priority": 1,
                "dependencies": [],
                "max_retries": 2,
                "retry_delay": 1
            }]
        )
    
    async def _decompose_chat(
        self,
        content: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> TaskDecomposition:
        """Decompose a chat task.
        
        Args:
            content: Task content
            context: Additional context
            
        Returns:
            TaskDecomposition: Decomposed task information
        """
        if "messages" not in content:
            raise ValueError("messages is required for chat")
        
        return TaskDecomposition(
            task_type="chat",
            subtasks=[{
                "name": "chat",
                "service": "chatbot",
                "data": {
                    "messages": content["messages"],
                    "context": context or {}
                },
                "priority": 1,
                "dependencies": [],
                "max_retries": 2,
                "retry_delay": 1
            }]
        )
    
    async def _decompose_web_research(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Decompose web research task."""
        return [
            {
                "type": "scrape_content",
                "service": "rag_scraper",
                "input": {
                    "url": content["url"],
                    "max_depth": content.get("max_depth", 1)
                }
            },
            {
                "type": "extract_info",
                "service": "chatbot",
                "input": {"content": "$scrape_content.output"}
            }
        ]
    
    async def _decompose_multi_stage_analysis(self, task: Dict[str, Any]) -> List[SubTask]:
        """Decompose multi-stage analysis task."""
        subtasks = []
        
        # Stage 1: Extract content
        if "document" in task["content"]:
            subtasks.append(SubTask(
                service="pdf_extraction",
                action="extract",
                data={"file": task["content"]["document"]},
                priority=1
            ))
        elif "urls" in task["content"]:
            subtasks.append(SubTask(
                service="rag_scraper",
                action="scrape",
                data={"urls": task["content"]["urls"]},
                priority=1
            ))
        
        # Stage 2: Analyze content
        subtasks.append(SubTask(
            service="sentiment_analysis",
            action="analyze",
            data={"text": ""},  # Will be filled from previous stage
            priority=2,
            dependencies=["pdf_extraction", "rag_scraper"]
        ))
        
        # Stage 3: Generate insights
        subtasks.append(SubTask(
            service="chatbot",
            action="analyze",
            data={
                "context": task.get("context", {}),
                "session_id": task.get("session_id")
            },
            priority=3,
            dependencies=["sentiment_analysis"]
        ))
        
        return subtasks

    async def _decompose_chat_with_context(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Decompose a chat with context task into subtasks.

        Args:
            content: Task content including message and preferences

        Returns:
            List of subtasks for processing chat with context
        """
        message = content.get("message", "")
        max_results = content.get("max_results", 5)
        session_id = content.get("session_id")

        subtasks = [
            {
                "service": "vector_db",
                "operation": "search",
                "params": {
                    "query": message,
                    "limit": max_results
                }
            },
            {
                "service": "chatbot",
                "operation": "generate_response",
                "params": {
                    "message": message,
                    "session_id": session_id
                },
                "depends_on": ["vector_db"]
            }
        ]

        return subtasks

    def _default_mock_response(self, task_type: str) -> TaskDecomposition:
        """Generate a default mock response for unknown task types."""
        return TaskDecomposition(
            task_type=task_type,
            subtasks=[{"type": "unknown", "service": "unknown"}],
            metadata={}
        )