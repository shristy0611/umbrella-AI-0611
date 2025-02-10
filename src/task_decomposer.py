from typing import Dict, Any, Optional
from pydantic import BaseModel

class SubTask(BaseModel):
    service: str
    action: str
    data: Dict[str, Any]
    priority: int = 1
    dependencies: list[str] = []

class TaskDecomposition(BaseModel):
    tasks: Dict[str, SubTask] = {}
    
    def add_task(self, task_id: str, task: SubTask):
        self.tasks[task_id] = task

class DynamicTaskDecomposer:
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        
    def _get_mock_response(self, task_type: str) -> TaskDecomposition:
        """Get mock response for testing."""
        decomposition = TaskDecomposition()
        
        if task_type == "document_analysis":
            decomposition.add_task("extract", SubTask(
                service="pdf_extraction",
                action="extract",
                data={"file": "test.pdf"},
                priority=1
            ))
            decomposition.add_task("analyze", SubTask(
                service="sentiment",
                action="analyze",
                data={"text": "$result.extract.text"},
                priority=2,
                dependencies=["extract"]
            ))
            
        elif task_type == "web_research":
            decomposition.add_task("scrape", SubTask(
                service="rag_scraper",
                action="scrape",
                data={"url": "http://test.com"},
                priority=1
            ))
            
        elif task_type == "chat_with_context":
            decomposition.add_task("retrieve", SubTask(
                service="vector_db",
                action="search",
                data={"query": "test query"},
                priority=1
            ))
            decomposition.add_task("respond", SubTask(
                service="chatbot",
                action="chat",
                data={
                    "message": "test message",
                    "context": "$result.retrieve.results"
                },
                priority=2,
                dependencies=["retrieve"]
            ))
            
        return decomposition
        
    async def decompose(self, task_type: str, content: dict, context: Optional[dict] = None) -> TaskDecomposition:
        """
        Decompose a task into subtasks based on its type and content.
        
        Args:
            task_type: The type of task to decompose
            content: The content/parameters for the task
            context: Optional context information for the task
            
        Returns:
            A TaskDecomposition object containing the subtasks and their dependencies
        """
        if self.use_mock:
            return self._get_mock_response(task_type)
            
        # Initialize task decomposition
        decomposition = TaskDecomposition()
        
        if task_type == "document_analysis":
            # Add PDF extraction task
            decomposition.add_task("extract", SubTask(
                service="pdf_extraction",
                action="extract",
                data={"file": content["file"]},
                priority=1
            ))
            
            # Add sentiment analysis task
            decomposition.add_task("sentiment", SubTask(
                service="sentiment",
                action="analyze",
                data={"text": "$result.extract.text"},
                priority=2,
                dependencies=["extract"]
            ))
            
        elif task_type == "web_research":
            # Add scraping task
            decomposition.add_task("scrape", SubTask(
                service="rag_scraper", 
                action="scrape",
                data={
                    "url": content["url"],
                    "max_depth": content.get("max_depth", 1)
                },
                priority=1
            ))
            
            # Add vector storage task
            decomposition.add_task("store", SubTask(
                service="vector_db",
                action="store",
                data={"content": "$result.scrape.content"},
                priority=2,
                dependencies=["scrape"]
            ))
            
        elif task_type == "chat_with_context":
            # Add context retrieval task
            decomposition.add_task("retrieve", SubTask(
                service="vector_db",
                action="search",
                data={
                    "query": content["message"],
                    "max_results": content.get("max_results", 3)
                },
                priority=1
            ))
            
            # Add chat response task
            decomposition.add_task("respond", SubTask(
                service="chatbot",
                action="chat",
                data={
                    "message": content["message"],
                    "context": "$result.retrieve.results",
                    "session_id": content.get("session_id")
                },
                priority=2,
                dependencies=["retrieve"]
            ))
            
        else:
            raise ValueError(f"No fallback workflow available for task type: {task_type}")
            
        return decomposition