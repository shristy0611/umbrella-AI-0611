"""Task decomposer module for breaking down tasks into subtasks."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class SubTask:
    """Subtask definition."""
    service: str
    content: Dict[str, Any]
    dependencies: List[str] = None
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass
class TaskDecomposition:
    """Task decomposition result."""
    subtasks: List[SubTask]
    metadata: Dict[str, Any]

class TaskDecomposer:
    """Decomposes tasks into subtasks that can be processed by services."""
    
    def __init__(self):
        """Initialize task decomposer."""
        self.decomposition_strategies = {
            "document_analysis": self._decompose_document_analysis,
            "chat_with_context": self._decompose_chat_with_context,
            "web_research": self._decompose_web_research,
            "sentiment_analysis": self._decompose_sentiment_analysis
        }
    
    async def decompose(
        self,
        task_type: str,
        content: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> TaskDecomposition:
        """Decompose a task into subtasks.
        
        Args:
            task_type: Type of task
            content: Task content
            context: Optional context
            
        Returns:
            TaskDecomposition: Decomposed task with subtasks
            
        Raises:
            ValueError: If task type is unknown
        """
        if task_type not in self.decomposition_strategies:
            raise ValueError(f"Unknown task type: {task_type}")
            
        strategy = self.decomposition_strategies[task_type]
        return await strategy(content, context or {})
    
    async def _decompose_document_analysis(
        self,
        content: Dict[str, Any],
        context: Dict[str, Any]
    ) -> TaskDecomposition:
        """Decompose document analysis task.
        
        Args:
            content: Task content
            context: Task context
            
        Returns:
            TaskDecomposition: Decomposed task
        """
        subtasks = []
        
        # PDF extraction
        if "file_id" in content:
            subtasks.append(SubTask(
                service="pdf_extraction",
                content={
                    "file_id": content["file_id"],
                    "extract_text": True,
                    "extract_metadata": True
                },
                dependencies=[]
            ))
        
        # Sentiment analysis
        if "sentiment" in content.get("analysis_types", []):
            subtasks.append(SubTask(
                service="sentiment_analysis",
                content={
                    "text": "$result.pdf_extraction.text",
                    "granularity": "document"
                },
                dependencies=["pdf_extraction"]
            ))
        
        # Topic analysis
        if "topics" in content.get("analysis_types", []):
            subtasks.append(SubTask(
                service="topic_analysis",
                content={
                    "text": "$result.pdf_extraction.text",
                    "num_topics": content.get("num_topics", 5)
                },
                dependencies=["pdf_extraction"]
            ))
        
        # Summary generation
        if "summary" in content.get("analysis_types", []):
            subtasks.append(SubTask(
                service="chatbot",
                content={
                    "messages": [
                        {
                            "role": "system",
                            "content": "Generate a concise summary of the following text."
                        },
                        {
                            "role": "user",
                            "content": "$result.pdf_extraction.text"
                        }
                    ],
                    "context": {
                        "sentiment": "$result.sentiment_analysis.sentiment",
                        "topics": "$result.topic_analysis.topics"
                    }
                },
                dependencies=["pdf_extraction", "sentiment_analysis", "topic_analysis"]
            ))
        
        return TaskDecomposition(
            subtasks=subtasks,
            metadata={"priority": context.get("priority", "normal")}
        )
    
    async def _decompose_chat_with_context(
        self,
        content: Dict[str, Any],
        context: Dict[str, Any]
    ) -> TaskDecomposition:
        """Decompose chat with context task.
        
        Args:
            content: Task content
            context: Task context
            
        Returns:
            TaskDecomposition: Decomposed task
        """
        subtasks = []
        
        # RAG query
        subtasks.append(SubTask(
            service="rag_scraper",
            content={
                "query": content["message"],
                "k": context.get("num_documents", 3)
            },
            dependencies=[]
        ))
        
        # Chat response
        subtasks.append(SubTask(
            service="chatbot",
            content={
                "messages": content["messages"],
                "context": {
                    "documents": "$result.rag_scraper.documents",
                    "session_id": content.get("session_id")
                }
            },
            dependencies=["rag_scraper"]
        ))
        
        return TaskDecomposition(
            subtasks=subtasks,
            metadata={"session_id": content.get("session_id")}
        )
    
    async def _decompose_web_research(
        self,
        content: Dict[str, Any],
        context: Dict[str, Any]
    ) -> TaskDecomposition:
        """Decompose web research task.
        
        Args:
            content: Task content
            context: Task context
            
        Returns:
            TaskDecomposition: Decomposed task
        """
        subtasks = []
        
        # Web scraping
        subtasks.append(SubTask(
            service="rag_scraper",
            content={
                "url": content["url"],
                "max_depth": content.get("max_depth", 2)
            },
            dependencies=[]
        ))
        
        # Content analysis
        if content.get("analyze", True):
            subtasks.append(SubTask(
                service="sentiment_analysis",
                content={
                    "text": "$result.rag_scraper.content",
                    "granularity": "document"
                },
                dependencies=["rag_scraper"]
            ))
            
            subtasks.append(SubTask(
                service="topic_analysis",
                content={
                    "text": "$result.rag_scraper.content",
                    "num_topics": content.get("num_topics", 5)
                },
                dependencies=["rag_scraper"]
            ))
        
        return TaskDecomposition(
            subtasks=subtasks,
            metadata={"url": content["url"]}
        )
    
    async def _decompose_sentiment_analysis(
        self,
        content: Dict[str, Any],
        context: Dict[str, Any]
    ) -> TaskDecomposition:
        """Decompose sentiment analysis task.
        
        Args:
            content: Task content
            context: Task context
            
        Returns:
            TaskDecomposition: Decomposed task
        """
        subtasks = [
            SubTask(
                service="sentiment_analysis",
                content={
                    "text": content["text"],
                    "granularity": content.get("granularity", "document"),
                    "aspects": content.get("aspects", [])
                },
                dependencies=[]
            )
        ]
        
        return TaskDecomposition(
            subtasks=subtasks,
            metadata={}
        ) 