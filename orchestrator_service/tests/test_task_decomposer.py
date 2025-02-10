import pytest
from src.task_decomposer import DynamicTaskDecomposer, TaskDecomposition, SubTask, TaskType, ServiceType

@pytest.fixture
def decomposer():
    """Create a task decomposer instance for testing"""
    return DynamicTaskDecomposer(use_mock=True)

@pytest.mark.asyncio
async def test_document_analysis_decomposition(decomposer):
    """Test decomposition of a document analysis task"""
    task_type = TaskType.DOCUMENT_ANALYSIS
    content = {
        "file": "test.pdf",
        "extract_images": True,
        "language": "en"
    }
    context = {
        "user_preferences": {
            "detailed_analysis": True
        }
    }
    
    result = await decomposer.decompose(task_type, content, context)
    
    assert isinstance(result, TaskDecomposition)
    assert len(result.tasks) == 3  # extract, analyze, store
    
    # Verify task structure
    assert "extract" in result.tasks
    assert "analyze" in result.tasks
    assert "store" in result.tasks
    
    # Verify services
    assert result.tasks["extract"].service == ServiceType.PDF_EXTRACTION
    assert result.tasks["analyze"].service == ServiceType.SENTIMENT
    assert result.tasks["store"].service == ServiceType.VECTOR_DB
    
    # Verify dependencies
    assert not result.tasks["extract"].dependencies
    assert result.tasks["analyze"].dependencies == ["extract"]
    assert set(result.tasks["store"].dependencies) == {"extract", "analyze"}

@pytest.mark.asyncio
async def test_web_research_decomposition(decomposer):
    """Test decomposition of a web research task"""
    task_type = TaskType.WEB_RESEARCH
    content = {
        "url": "https://example.com",
        "max_depth": 2,
        "selectors": ["article", "p"]
    }
    
    result = await decomposer.decompose(task_type, content)
    
    assert isinstance(result, TaskDecomposition)
    assert len(result.tasks) == 3  # scrape, analyze, store
    
    # Verify task structure
    assert "scrape" in result.tasks
    assert "analyze" in result.tasks
    assert "store" in result.tasks
    
    # Verify services
    assert result.tasks["scrape"].service == ServiceType.RAG_SCRAPER
    assert result.tasks["analyze"].service == ServiceType.SENTIMENT
    assert result.tasks["store"].service == ServiceType.VECTOR_DB
    
    # Verify dependencies
    assert not result.tasks["scrape"].dependencies
    assert result.tasks["analyze"].dependencies == ["scrape"]
    assert set(result.tasks["store"].dependencies) == {"scrape", "analyze"}
    
    # Verify content passed through
    assert result.tasks["scrape"].data["url"] == content["url"]
    assert result.tasks["scrape"].data["max_depth"] == content["max_depth"]
    assert result.tasks["scrape"].data["selectors"] == content["selectors"]

@pytest.mark.asyncio
async def test_chat_with_context_decomposition(decomposer):
    """Test decomposition of a chat with context task"""
    task_type = TaskType.CHAT_WITH_CONTEXT
    content = {
        "message": "What do you know about machine learning?",
        "session_id": "test-session",
        "max_results": 5
    }
    context = {
        "user_preferences": {
            "response_style": "detailed"
        }
    }
    
    result = await decomposer.decompose(task_type, content, context)
    
    assert isinstance(result, TaskDecomposition)
    assert len(result.tasks) == 2  # retrieve, respond
    
    # Verify task structure
    assert "retrieve" in result.tasks
    assert "respond" in result.tasks
    
    # Verify services
    assert result.tasks["retrieve"].service == ServiceType.VECTOR_DB
    assert result.tasks["respond"].service == ServiceType.CHATBOT
    
    # Verify dependencies
    assert not result.tasks["retrieve"].dependencies
    assert result.tasks["respond"].dependencies == ["retrieve"]
    
    # Verify content and context passed through
    assert result.tasks["retrieve"].data["query"] == content["message"]
    assert result.tasks["retrieve"].data["max_results"] == content["max_results"]
    assert result.tasks["respond"].data["session_id"] == content["session_id"]
    assert result.tasks["respond"].data["user_preferences"] == context["user_preferences"]

@pytest.mark.asyncio
async def test_invalid_task_type(decomposer):
    """Test handling of invalid task type"""
    with pytest.raises(ValueError, match="Unsupported task type: invalid_task"):
        await decomposer.decompose("invalid_task", {})

@pytest.mark.asyncio
async def test_missing_required_content(decomposer):
    """Test handling of missing required content"""
    task_type = TaskType.DOCUMENT_ANALYSIS
    content = {}  # Missing required 'file' field
    
    with pytest.raises(KeyError):
        await decomposer.decompose(task_type, content)

@pytest.mark.asyncio
async def test_task_priorities(decomposer):
    """Test that task priorities are properly set"""
    task_type = TaskType.DOCUMENT_ANALYSIS
    content = {"file": "test.pdf"}
    
    result = await decomposer.decompose(task_type, content)
    
    # Verify priority ordering
    assert result.tasks["extract"].priority == 1
    assert result.tasks["analyze"].priority == 2
    assert result.tasks["store"].priority == 3