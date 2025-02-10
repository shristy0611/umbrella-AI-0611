import pytest
from unittest.mock import Mock, patch, AsyncMock
from chatbot_service.src.chatbot import Chatbot
from shared.base_service import BaseService
import json

@pytest.fixture
def chatbot():
    return Chatbot()

@pytest.fixture
def sample_context():
    return [
        {
            "text": "The product launched in 2022.",
            "metadata": {"source": "product_info.pdf", "relevance": 0.95}
        },
        {
            "text": "Key features include AI assistance and cloud integration.",
            "metadata": {"source": "features.pdf", "relevance": 0.85}
        }
    ]

@pytest.fixture
def sample_conversation_history():
    return [
        {"role": "user", "content": "What are the key features?"},
        {"role": "assistant", "content": "The key features include AI assistance and cloud integration."},
        {"role": "user", "content": "When was it launched?"}
    ]

@pytest.mark.asyncio
async def test_chat_with_context(chatbot, sample_context):
    """Test chatbot response with context."""
    message = "When was the product launched?"
    
    result = await chatbot.generate_response(message, context=sample_context)
    
    assert isinstance(result, dict)
    assert "response" in result
    assert isinstance(result["response"], str)
    assert len(result["response"]) > 0
    assert "2022" in result["response"]  # Should reference context
    assert "metadata" in result
    assert "sources_used" in result["metadata"]

@pytest.mark.asyncio
async def test_chat_with_conversation_history(chatbot, sample_conversation_history):
    """Test chatbot response with conversation history."""
    message = "Tell me more about those features"
    
    result = await chatbot.generate_response(
        message,
        conversation_history=sample_conversation_history
    )
    
    assert isinstance(result, dict)
    assert "response" in result
    assert "AI" in result["response"]  # Should reference previous conversation
    assert "cloud" in result["response"]

@pytest.mark.asyncio
async def test_chat_with_user_preferences(chatbot):
    """Test chatbot response with user preferences."""
    message = "Tell me about the product"
    preferences = {
        "language": "en",
        "response_style": "technical",
        "max_length": 100
    }
    
    result = await chatbot.generate_response(message, user_preferences=preferences)
    
    assert isinstance(result, dict)
    assert "response" in result
    assert len(result["response"].split()) <= preferences["max_length"]

@pytest.mark.asyncio
async def test_handle_empty_message(chatbot):
    """Test handling of empty messages."""
    with pytest.raises(ValueError) as exc_info:
        await chatbot.generate_response("")
    assert "Empty message" in str(exc_info.value)

@pytest.mark.asyncio
async def test_handle_very_long_message(chatbot):
    """Test handling of very long messages."""
    very_long_message = "test " * 1000
    
    result = await chatbot.generate_response(very_long_message)
    
    assert isinstance(result, dict)
    assert "response" in result
    assert "truncated_input" in result["metadata"]
    assert result["metadata"]["truncated_input"] is True

@pytest.mark.asyncio
async def test_process_request_with_valid_message(chatbot, sample_context):
    """Test processing a valid request through the service interface."""
    request_data = {
        "message": "When was the product launched?",
        "context": sample_context,
        "options": {
            "max_length": 100,
            "temperature": 0.7
        }
    }
    
    result = await chatbot.process_request(request_data)
    
    assert isinstance(result, dict)
    assert "response" in result
    assert "metadata" in result

@pytest.mark.asyncio
async def test_process_request_with_missing_message():
    """Test processing request with missing message."""
    bot = Chatbot()
    request_data = {
        "context": [],
        "options": {}
    }
    
    with pytest.raises(ValueError) as exc_info:
        await bot.process_request(request_data)
    assert "Missing message" in str(exc_info.value)

@pytest.mark.asyncio
async def test_session_management(chatbot):
    """Test chat session management."""
    session_id = "test_session"
    
    # First message in session
    result1 = await chatbot.generate_response(
        "What are the features?",
        session_id=session_id
    )
    
    # Second message in same session
    result2 = await chatbot.generate_response(
        "Tell me more",
        session_id=session_id
    )
    
    assert "session_id" in result1["metadata"]
    assert "session_id" in result2["metadata"]
    assert result1["metadata"]["session_id"] == session_id
    assert result2["metadata"]["session_id"] == session_id

@pytest.mark.asyncio
async def test_response_streaming(chatbot):
    """Test streaming response generation."""
    message = "Tell me about the product"
    
    async for chunk in chatbot.generate_response_stream(message):
        assert isinstance(chunk, str)
        assert len(chunk) > 0

@pytest.mark.asyncio
async def test_context_relevance_threshold(chatbot, sample_context):
    """Test context filtering based on relevance threshold."""
    message = "What are the features?"
    threshold = 0.9
    
    result = await chatbot.generate_response(
        message,
        context=sample_context,
        relevance_threshold=threshold
    )
    
    used_sources = result["metadata"]["sources_used"]
    assert all(source["relevance"] >= threshold for source in used_sources)

@pytest.mark.asyncio
async def test_error_handling(chatbot):
    """Test error handling during response generation."""
    with patch.object(chatbot, '_generate_response', side_effect=Exception("API Error")):
        with pytest.raises(Exception) as exc_info:
            await chatbot.generate_response("Test message")
        assert "API Error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_response_formatting(chatbot):
    """Test response formatting options."""
    message = "List the features"
    format_options = {
        "style": "bullet_points",
        "include_sources": True
    }
    
    result = await chatbot.generate_response(
        message,
        format_options=format_options
    )
    
    assert isinstance(result, dict)
    assert "response" in result
    assert "•" in result["response"] or "-" in result["response"]  # Check for bullet points
    assert "sources" in result["metadata"] 