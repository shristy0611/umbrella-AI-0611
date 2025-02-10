import pytest
from src.orchestrator.task_decomposer import DynamicTaskDecomposer, TaskDecomposition, SubTask

@pytest.fixture
def decomposer():
    """Create a DynamicTaskDecomposer instance for testing"""
    return DynamicTaskDecomposer(use_mock=True)

@pytest.mark.asyncio
async def test_document_analysis_decomposition(decomposer):
    """Test decomposition of a document analysis task"""
    task_type = "document_analysis"
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
    assert len(result.subtasks) == 3
    
    # Verify task dependencies
    pdf_extractor = next(st for st in result.subtasks if st.service == "pdf_extractor")
    sentiment_analyzer = next(st for st in result.subtasks if st.service == "sentiment_analyzer")
    chatbot = next(st for st in result.subtasks if st.service == "chatbot")
    
    assert pdf_extractor.dependencies is None
    assert sentiment_analyzer.dependencies == ["pdf_extractor"]
    assert chatbot.dependencies == ["sentiment_analyzer"]

@pytest.mark.asyncio
async def test_web_research_decomposition(decomposer):
    """Test decomposition of a web research task"""
    task_type = "web_research"
    content = {
        "url": "https://example.com",
        "max_depth": 2,
        "follow_links": True
    }
    
    result = await decomposer.decompose(task_type, content)
    
    assert isinstance(result, TaskDecomposition)
    assert len(result.subtasks) == 2
    
    # Verify task structure
    web_scraper = next(st for st in result.subtasks if st.service == "web_scraper")
    content_analyzer = next(st for st in result.subtasks if st.service == "content_analyzer")
    
    assert web_scraper.dependencies is None
    assert content_analyzer.dependencies == ["web_scraper"]

@pytest.mark.asyncio
async def test_custom_workflow_decomposition(decomposer):
    """Test decomposition of a custom workflow with complex dependencies"""
    task_type = "custom_analysis"
    content = {
        "sources": [
            {"type": "pdf", "file": "doc1.pdf"},
            {"type": "web", "url": "https://example.com"}
        ],
        "analysis_type": "comparative"
    }
    
    with pytest.raises(ValueError, match="No fallback workflow available for task type: custom_analysis"):
        await decomposer.decompose(task_type, content)

@pytest.mark.asyncio
async def test_validation_error_handling(decomposer):
    """Test handling of validation errors in task decomposition"""
    task_type = "document_analysis"
    content = {"file": "test.pdf"}
    
    result = await decomposer.decompose(task_type, content)
    assert isinstance(result, TaskDecomposition)
    assert len(result.subtasks) == 3
    assert all(isinstance(subtask, SubTask) for subtask in result.subtasks)

@pytest.mark.asyncio
async def test_dependency_resolution(decomposer):
    """Test that task dependencies are properly resolved"""
    task_type = "document_analysis"
    content = {"file": "test.pdf"}
    
    result = await decomposer.decompose(task_type, content)
    assert isinstance(result, TaskDecomposition)
    
    # Verify dependency chain
    pdf_extractor = next(st for st in result.subtasks if st.service == "pdf_extractor")
    sentiment_analyzer = next(st for st in result.subtasks if st.service == "sentiment_analyzer")
    chatbot = next(st for st in result.subtasks if st.service == "chatbot")
    
    assert pdf_extractor.dependencies is None
    assert sentiment_analyzer.dependencies == ["pdf_extractor"]
    assert chatbot.dependencies == ["sentiment_analyzer"] 