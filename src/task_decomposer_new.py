from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

class SubTask(BaseModel):
    """A single subtask in the decomposition"""
    service: str
    description: str
    dependencies: Optional[List[str]] = None

class TaskDecomposition(BaseModel):
    """The complete decomposition of a task into subtasks"""
    subtasks: List[SubTask]

class MockLLM:
    """A mock LLM for testing purposes"""
    async def ainvoke(self, prompt: str) -> Dict[str, Any]:
        if "document" in prompt.lower():
            return {
                "subtasks": [
                    {"service": "pdf_extractor", "description": "Extract text and structure from PDF", "dependencies": None},
                    {"service": "sentiment_analyzer", "description": "Analyze sentiment in extracted text", "dependencies": ["pdf_extractor"]},
                    {"service": "chatbot", "description": "Generate insights from analysis", "dependencies": ["sentiment_analyzer"]}
                ]
            }
        elif "web" in prompt.lower():
            return {
                "subtasks": [
                    {"service": "web_scraper", "description": "Scrape content from URL", "dependencies": None},
                    {"service": "content_analyzer", "description": "Analyze scraped content", "dependencies": ["web_scraper"]}
                ]
            }
        else:
            raise ValueError(f"No predefined response for prompt: {prompt}")

class DynamicTaskDecomposer:
    """Decomposes tasks into subtasks using LLM"""
    
    def __init__(self, use_mock: bool = False):
        """Initialize the task decomposer.
        
        Args:
            use_mock (bool): Whether to use a mock LLM for testing
        """
        self.llm = MockLLM() if use_mock else None
        self.parser = PydanticOutputParser(pydantic_object=TaskDecomposition)
        self.prompt_template = PromptTemplate(
            template="""Decompose the following task into subtasks:
            Task Type: {task_type}
            Content: {content}
            Context: {context}
            
            Return a JSON with subtasks array where each subtask has:
            - service: the service to handle this subtask
            - description: what needs to be done
            - dependencies: list of services this subtask depends on (or null)
            """,
            input_variables=["task_type", "content", "context"]
        )

    async def decompose(self, task_type: str, content: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskDecomposition:
        """Decompose a task into subtasks.
        
        Args:
            task_type (str): The type of task to decompose
            content (Dict[str, Any]): The content/parameters of the task
            context (Optional[Dict[str, Any]], optional): Additional context for task decomposition. Defaults to None.
            
        Returns:
            TaskDecomposition: The decomposed task with subtasks
            
        Raises:
            ValueError: If no LLM is available and task type is not supported
        """
        try:
            if not self.llm:
                raise ValueError("No LLM available for dynamic decomposition")
            
            prompt = self.prompt_template.format(
                task_type=task_type,
                content=content,
                context=context or {}
            )
            
            llm_response = await self.llm.ainvoke(prompt)
            return TaskDecomposition(**llm_response)
            
        except Exception as e:
            # Fallback to predefined workflows
            if task_type == "document_analysis":
                return TaskDecomposition(subtasks=[
                    SubTask(service="pdf_extractor", description="Extract text and structure from PDF"),
                    SubTask(service="sentiment_analyzer", description="Analyze sentiment in extracted text", dependencies=["pdf_extractor"]),
                    SubTask(service="chatbot", description="Generate insights from analysis", dependencies=["sentiment_analyzer"])
                ])
            elif task_type == "web_research":
                return TaskDecomposition(subtasks=[
                    SubTask(service="web_scraper", description="Scrape content from URL"),
                    SubTask(service="content_analyzer", description="Analyze scraped content", dependencies=["web_scraper"])
                ])
            else:
                raise ValueError(f"No fallback workflow available for task type: {task_type}") 