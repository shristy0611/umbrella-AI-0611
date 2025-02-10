import pytest
from orchestrator_service.src.task_decomposer import DynamicTaskDecomposer, TaskType, ServiceType, SubTask

@pytest.fixture
def decomposer():
    return DynamicTaskDecomposer()

def test_document_analysis_decomposition(decomposer):
    """Test document analysis task decomposition."""
    task_data = {
        "file_path": "test.pdf"
    }
    
    tasks = decomposer.decompose_task(TaskType.DOCUMENT_ANALYSIS, task_data)
    
    assert len(tasks) == 3
    assert "extract" in tasks
    assert "analyze" in tasks
    assert "store" in tasks
    
    # Verify PDF extraction task
    extract_task = tasks["extract"]
    assert extract_task.service == ServiceType.PDF_EXTRACTION
    assert extract_task.action == "extract"
    assert extract_task.data["file"] == "test.pdf"
    assert extract_task.priority == 1
    assert not extract_task.dependencies
    
    # Verify sentiment analysis task
    analyze_task = tasks["analyze"]
    assert analyze_task.service == ServiceType.SENTIMENT
    assert analyze_task.action == "analyze"
    assert analyze_task.data["text"] == "$result.extract.text"
    assert analyze_task.priority == 2
    assert analyze_task.dependencies == ["extract"]
    
    # Verify vector storage task
    store_task = tasks["store"]
    assert store_task.service == ServiceType.VECTOR_DB
    assert store_task.action == "store"
    assert store_task.data["text"] == "$result.extract.text"
    assert store_task.data["metadata"]["sentiment"] == "$result.analyze.sentiment"
    assert store_task.priority == 3
    assert set(store_task.dependencies) == {"extract", "analyze"}

def test_web_research_decomposition(decomposer):
    """Test web research task decomposition."""
    task_data = {
        "url": "https://example.com",
        "max_depth": 2
    }
    
    tasks = decomposer.decompose_task(TaskType.WEB_RESEARCH, task_data)
    
    assert len(tasks) == 2
    assert "scrape" in tasks
    assert "store" in tasks
    
    # Verify scraping task
    scrape_task = tasks["scrape"]
    assert scrape_task.service == ServiceType.RAG_SCRAPER
    assert scrape_task.action == "scrape"
    assert scrape_task.data["url"] == "https://example.com"
    assert scrape_task.data["max_depth"] == 2
    assert scrape_task.priority == 1
    assert not scrape_task.dependencies
    
    # Verify storage task
    store_task = tasks["store"]
    assert store_task.service == ServiceType.VECTOR_DB
    assert store_task.action == "store"
    assert store_task.data["text"] == "$result.scrape.content"
    assert store_task.priority == 2
    assert store_task.dependencies == ["scrape"]

def test_chat_with_context_decomposition(decomposer):
    """Test chat with context task decomposition."""
    task_data = {
        "query": "What is the weather like?"
    }
    
    tasks = decomposer.decompose_task(TaskType.CHAT_WITH_CONTEXT, task_data)
    
    assert len(tasks) == 2
    assert "query" in tasks
    assert "chat" in tasks
    
    # Verify query task
    query_task = tasks["query"]
    assert query_task.service == ServiceType.VECTOR_DB
    assert query_task.action == "query"
    assert query_task.data["text"] == "What is the weather like?"
    assert query_task.priority == 1
    assert not query_task.dependencies
    
    # Verify chat task
    chat_task = tasks["chat"]
    assert chat_task.service == ServiceType.CHATBOT
    assert chat_task.action == "chat"
    assert chat_task.data["query"] == "What is the weather like?"
    assert chat_task.data["context"] == "$result.query.results"
    assert chat_task.priority == 2
    assert chat_task.dependencies == ["query"]

def test_invalid_task_type(decomposer):
    """Test handling of invalid task type."""
    with pytest.raises(ValueError, match="Unknown task type"):
        decomposer.decompose_task("invalid_type", {}) 