from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import json
import os
from enum import Enum
from shared.logging_utils import setup_logger, with_correlation_id

# Set up logger for this module
logger = setup_logger('orchestrator.task_decomposer')

class TaskType(str, Enum):
    """Supported task types in the system"""
    DOCUMENT_ANALYSIS = "document_analysis"
    WEB_RESEARCH = "web_research"
    CHAT_WITH_CONTEXT = "chat_with_context"

class ServiceType(str, Enum):
    """Available services in the system"""
    PDF_EXTRACTION = "pdf_extraction"
    SENTIMENT = "sentiment"
    CHATBOT = "chatbot"
    RAG_SCRAPER = "rag_scraper"
    VECTOR_DB = "vector_db"

class SubTask(BaseModel):
    """A single subtask in the decomposed task."""
    service: ServiceType
    action: str = Field(description="The action to perform (e.g., 'extract', 'analyze')")
    data: Dict[str, Any] = Field(description="Parameters for the action")
    priority: int = Field(default=1, description="Task priority (lower numbers run first)")
    dependencies: Optional[List[str]] = Field(default_factory=list, description="List of task IDs that must complete before this task")

class TaskDecomposition(BaseModel):
    """The complete task decomposition result."""
    tasks: Dict[str, SubTask] = Field(default_factory=dict, description="Map of task ID to subtask")
    
    def add_task(self, task_id: str, task: SubTask):
        """Add a task to the decomposition"""
        self.tasks[task_id] = task

class DynamicTaskDecomposer:
    """Handles dynamic task decomposition for the orchestrator."""
    
    def __init__(self, use_mock: bool = False):
        """Initialize the task decomposer.
        
        Args:
            use_mock (bool): Whether to use mock responses for testing
        """
        self.use_mock = use_mock
        logger.info("Initialized DynamicTaskDecomposer with use_mock=%s", use_mock)
        self.task_types = {
            TaskType.DOCUMENT_ANALYSIS: self._decompose_document_analysis,
            TaskType.WEB_RESEARCH: self._decompose_web_research,
            TaskType.CHAT_WITH_CONTEXT: self._decompose_chat_with_context
        }
    
    def _get_mock_response(self, task_type: str) -> TaskDecomposition:
        """Get mock response for testing."""
        logger.debug("Generating mock response for task_type: %s", task_type)
        decomposition = TaskDecomposition()
        
        if task_type == TaskType.DOCUMENT_ANALYSIS:
            decomposition.add_task("extract", SubTask(
                service=ServiceType.PDF_EXTRACTION,
                action="extract",
                data={"file": "test.pdf"},
                priority=1
            ))
            decomposition.add_task("analyze", SubTask(
                service=ServiceType.SENTIMENT,
                action="analyze",
                data={"text": "$result.extract.text"},
                priority=2,
                dependencies=["extract"]
            ))
            decomposition.add_task("store", SubTask(
                service=ServiceType.VECTOR_DB,
                action="store",
                data={"text": "$result.extract.text", "metadata": {"sentiment": "$result.analyze.sentiment"}},
                priority=3,
                dependencies=["extract", "analyze"]
            ))
            
        elif task_type == TaskType.WEB_RESEARCH:
            decomposition.add_task("scrape", SubTask(
                service=ServiceType.RAG_SCRAPER,
                action="scrape",
                data={"url": "http://test.com", "max_depth": 1},
                priority=1
            ))
            decomposition.add_task("analyze", SubTask(
                service=ServiceType.SENTIMENT,
                action="analyze",
                data={"text": "$result.scrape.content"},
                priority=2,
                dependencies=["scrape"]
            ))
            decomposition.add_task("store", SubTask(
                service=ServiceType.VECTOR_DB,
                action="store",
                data={"content": "$result.scrape.content", "metadata": {"sentiment": "$result.analyze.sentiment"}},
                priority=3,
                dependencies=["scrape", "analyze"]
            ))
            
        elif task_type == TaskType.CHAT_WITH_CONTEXT:
            decomposition.add_task("retrieve", SubTask(
                service=ServiceType.VECTOR_DB,
                action="search",
                data={"query": "test query"},
                priority=1
            ))
            decomposition.add_task("respond", SubTask(
                service=ServiceType.CHATBOT,
                action="chat",
                data={
                    "message": "test message",
                    "context": "$result.retrieve.results"
                },
                priority=2,
                dependencies=["retrieve"]
            ))
            
        logger.debug("Generated mock decomposition with %d tasks", len(decomposition.tasks))
        return decomposition
        
    @with_correlation_id
    async def decompose(self, task_type: str, content: Dict[str, Any], context: Optional[Dict[str, Any]] = None, correlation_id: Optional[str] = None) -> TaskDecomposition:
        """
        Decompose a task into subtasks based on its type and content.
        
        Args:
            task_type: The type of task to decompose
            content: The content/parameters for the task
            context: Optional context information for the task
            correlation_id: Optional correlation ID for request tracing
            
        Returns:
            A TaskDecomposition object containing the subtasks and their dependencies
            
        Raises:
            ValueError: If the task type is not supported
        """
        logger.info("Starting task decomposition for type=%s", task_type)
        logger.debug("Task content: %s", content)
        logger.debug("Task context: %s", context)
        
        if not TaskType(task_type):
            logger.error("Unsupported task type: %s", task_type)
            raise ValueError(f"Unsupported task type: {task_type}")
            
        if self.use_mock:
            logger.info("Using mock response for task decomposition")
            return self._get_mock_response(task_type)
            
        # Initialize task decomposition
        decomposition = TaskDecomposition()
        
        try:
            if task_type in self.task_types:
                logger.info(f"Decomposing {task_type} task")
                tasks = self.task_types[task_type](content)
                decomposition.tasks.update(tasks)
            else:
                logger.error("Unsupported task type: %s", task_type)
                raise ValueError(f"Unsupported task type: {task_type}")
            
            logger.info("Successfully decomposed task into %d subtasks", len(decomposition.tasks))
            return decomposition
            
        except Exception as e:
            logger.error("Error during task decomposition: %s", str(e), exc_info=True)
            raise 

    def _decompose_document_analysis(self, task_data: Dict[str, Any]) -> Dict[str, SubTask]:
        tasks = {}
        
        # PDF extraction task
        tasks["extract"] = SubTask(
            service=ServiceType.PDF_EXTRACTION,
            action="extract",
            data={"file": task_data["file_path"]},
            priority=1
        )
        
        # Sentiment analysis task
        tasks["analyze"] = SubTask(
            service=ServiceType.SENTIMENT,
            action="analyze",
            data={"text": "$result.extract.text"},
            priority=2,
            dependencies=["extract"]
        )
        
        # Store in vector DB
        tasks["store"] = SubTask(
            service=ServiceType.VECTOR_DB,
            action="store",
            data={
                "text": "$result.extract.text",
                "metadata": {"sentiment": "$result.analyze.sentiment"}
            },
            priority=3,
            dependencies=["extract", "analyze"]
        )
        
        return tasks

    def _decompose_web_research(self, task_data: Dict[str, Any]) -> Dict[str, SubTask]:
        tasks = {}
        
        # Web scraping task
        tasks["scrape"] = SubTask(
            service=ServiceType.RAG_SCRAPER,
            action="scrape",
            data={"url": task_data["url"], "max_depth": task_data.get("max_depth", 1)},
            priority=1
        )
        
        # Store scraped content
        tasks["store"] = SubTask(
            service=ServiceType.VECTOR_DB,
            action="store",
            data={"text": "$result.scrape.content"},
            priority=2,
            dependencies=["scrape"]
        )
        
        return tasks

    def _decompose_chat_with_context(self, task_data: Dict[str, Any]) -> Dict[str, SubTask]:
        tasks = {}
        
        # Query vector DB for context
        tasks["query"] = SubTask(
            service=ServiceType.VECTOR_DB,
            action="query",
            data={"text": task_data["query"]},
            priority=1
        )
        
        # Chat with context
        tasks["chat"] = SubTask(
            service=ServiceType.CHATBOT,
            action="chat",
            data={
                "query": task_data["query"],
                "context": "$result.query.results"
            },
            priority=2,
            dependencies=["query"]
        )
        
        return tasks 

    def decompose_task(self, task_type: TaskType, task_data: Dict[str, Any]) -> Dict[str, SubTask]:
        """
        Decompose a task into subtasks based on its type and content.
        
        Args:
            task_type: The type of task to decompose
            task_data: The content/parameters for the task
            
        Returns:
            A dictionary mapping task IDs to SubTask objects
            
        Raises:
            ValueError: If the task type is not supported
        """
        if not isinstance(task_type, TaskType):
            raise ValueError(f"Unknown task type: {task_type}")
            
        if task_type not in self.task_types:
            raise ValueError(f"Unsupported task type: {task_type}")
            
        return self.task_types[task_type](task_data) 