"""Unit tests for Gemini API interactions with mocked responses and response validation."""

import os
import pytest
import asyncio
import logging
from unittest.mock import Mock, patch, AsyncMock
from PIL import Image
from io import BytesIO
import google.generativeai as genai
from shared.gemini import (
    GeminiTextChat,
    GeminiSingleImage,
    GeminiMultiImage,
    GeminiFileUpload,
    GeminiMultiTurnChat,
    gemini_config
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test data
TEST_PROMPT = "What do you see in this image?"
TEST_CHAT_PROMPT = "Tell me a short story about a robot learning to paint."
TEST_CONTEXT = "You are an art critic reviewing paintings."

# Expected response formats with realistic content patterns
EXPECTED_TEXT_RESPONSE = {
    "story": """In a small studio, a robot named Arc-2 discovered a set of paintbrushes. 
    With mechanical precision, it began to learn the art of painting, analyzing brush strokes 
    and color theory through its visual sensors.""",
    "length_range": (50, 1000),
    "required_elements": ["robot", "paint", "learn"]
}

EXPECTED_IMAGE_RESPONSE = {
    "description": """In this image, I can see a solid red square. The image has dimensions 
    of 100x100 pixels. The color appears to be a pure red with no variations or patterns.""",
    "length_range": (30, 500),
    "required_elements": ["red", "square", "pixels"]
}

EXPECTED_MULTI_IMAGE_RESPONSE = {
    "comparison": """When comparing these two images, I observe they are identical red squares. 
    Key similarities: both are 100x100 pixels, both show a solid red color, and both are perfect squares. 
    I cannot detect any differences between them.""",
    "length_range": (50, 1000),
    "required_elements": ["identical", "similarities", "differences"]
}

class MockResponse:
    """Enhanced mock response object that mimics Gemini API response structure."""
    def __init__(self, text, response_type="text"):
        self.text = text.strip()  # Remove leading/trailing whitespace
        self.response_type = response_type
        self.candidates = [Mock(content=Mock(text=text.strip()))]
        self.safety_ratings = [
            Mock(category="HARM_CATEGORY_HARASSMENT", probability="NEGLIGIBLE"),
            Mock(category="HARM_CATEGORY_HATE_SPEECH", probability="NEGLIGIBLE")
        ]
        self.prompt_feedback = Mock(
            block_reason=None,
            safety_ratings=[
                Mock(category="HARM_CATEGORY_DANGEROUS", probability="NEGLIGIBLE")
            ]
        )

def validate_response(response, expected_format, response_type):
    """Validate response against expected format and log results."""
    logger.info(f"Validating {response_type} response: {response.text[:100]}...")
    
    # Check response length
    length = len(response.text)
    min_length, max_length = expected_format["length_range"]
    assert min_length <= length <= max_length, f"Response length {length} outside expected range {expected_format['length_range']}"
    logger.info(f"Length validation passed: {length} characters")
    
    # Check required elements
    for element in expected_format["required_elements"]:
        assert element.lower() in response.text.lower(), f"Missing required element: {element}"
    logger.info("Required elements validation passed")
    
    # Check safety ratings
    assert hasattr(response, "safety_ratings"), "Response missing safety ratings"
    assert all(rating.probability == "NEGLIGIBLE" for rating in response.safety_ratings), \
        "Found non-negligible safety ratings"
    logger.info("Safety ratings validation passed")
    
    return True

@pytest.fixture
def setup_env():
    """Set up test environment."""
    original_env = {}
    if 'GEMINI_API_KEY' in os.environ:
        original_env['GEMINI_API_KEY'] = os.environ['GEMINI_API_KEY']
    os.environ['GEMINI_API_KEY'] = 'test_key'
    yield
    for key, value in original_env.items():
        os.environ[key] = value

@pytest.fixture
def mock_image():
    """Create a mock PIL Image."""
    return Image.new('RGB', (100, 100), color='red')

@pytest.mark.asyncio
@patch('google.generativeai.GenerativeModel')
async def test_text_chat_mocked(mock_model, setup_env):
    """Test text chat functionality with enhanced response validation."""
    mock_chat = AsyncMock()
    mock_response = MockResponse(EXPECTED_TEXT_RESPONSE["story"], "text")
    mock_chat.send_message_async = AsyncMock(return_value=mock_response)
    mock_model.return_value.start_chat.return_value = mock_chat
    
    chat = GeminiTextChat()
    await chat.start_text_chat()
    
    response = await chat.send_message(TEST_CHAT_PROMPT)
    assert validate_response(response, EXPECTED_TEXT_RESPONSE, "text")
    mock_chat.send_message_async.assert_called_once_with(TEST_CHAT_PROMPT)
    logger.info("Text chat test completed successfully")

@pytest.mark.asyncio
@patch('google.generativeai.GenerativeModel')
async def test_single_image_mocked(mock_model, setup_env, mock_image):
    """Test single image processing with enhanced response validation."""
    mock_response = MockResponse(EXPECTED_IMAGE_RESPONSE["description"], "image")
    mock_model.return_value.generate_content_async = AsyncMock(return_value=mock_response)
    
    processor = GeminiSingleImage()
    response = await processor.process_single_image(mock_image, TEST_PROMPT)
    
    assert validate_response(response, EXPECTED_IMAGE_RESPONSE, "image")
    mock_model.return_value.generate_content_async.assert_called_once()
    logger.info("Single image test completed successfully")

@pytest.mark.asyncio
@patch('google.generativeai.GenerativeModel')
async def test_multiple_images_mocked(mock_model, setup_env, mock_image):
    """Test multiple image processing with enhanced response validation."""
    mock_response = MockResponse(EXPECTED_MULTI_IMAGE_RESPONSE["comparison"], "multi_image")
    mock_model.return_value.generate_content_async = AsyncMock(return_value=mock_response)
    
    processor = GeminiMultiImage()
    images = [mock_image, mock_image]
    response = await processor.process_multiple_images(images, "Compare these images")
    
    assert validate_response(response, EXPECTED_MULTI_IMAGE_RESPONSE, "multi_image")
    mock_model.return_value.generate_content_async.assert_called_once()
    logger.info("Multiple images test completed successfully")

@pytest.mark.asyncio
@patch('google.generativeai.GenerativeModel')
async def test_file_upload_mocked(mock_model, setup_env, tmp_path):
    """Test file upload and processing with enhanced response validation."""
    mock_response = MockResponse(
        "The text file contains: Test content. This appears to be a simple text document...",
        "file"
    )
    mock_model.return_value.generate_content_async = AsyncMock(return_value=mock_response)
    
    # Create temporary test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    processor = GeminiFileUpload()
    response = await processor.process_file(
        str(test_file),
        TEST_PROMPT,
        mime_type="text/plain"
    )
    
    # Define expected format for file content response
    expected_file_response = {
        "length_range": (30, 500),
        "required_elements": ["content", "text", "document"],
    }
    
    assert validate_response(response, expected_file_response, "file")
    mock_model.return_value.generate_content_async.assert_called_once()
    logger.info("File upload test completed successfully")

@pytest.mark.asyncio
@patch('google.generativeai.GenerativeModel')
async def test_multi_turn_chat_mocked(mock_model, setup_env):
    """Test multi-turn chat functionality with enhanced response validation."""
    mock_chat = AsyncMock()
    
    # Define expected formats for each turn
    first_turn_response = {
        "length_range": (20, 500),
        "required_elements": ["art", "critic"],
    }
    second_turn_response = {
        "length_range": (20, 500),
        "required_elements": ["painting", "art"],
    }
    
    mock_chat.send_message_async = AsyncMock(side_effect=[
        MockResponse("As an art critic, I analyze paintings with a keen eye for detail...", "chat"),
        MockResponse("The painting exhibits remarkable artistry in its composition...", "chat")
    ])
    mock_model.return_value.start_chat.return_value = mock_chat
    
    chat = GeminiMultiTurnChat()
    await chat.start_chat_session(TEST_CONTEXT)
    
    # Test first message
    response1 = await chat.send_message("First message")
    assert validate_response(response1, first_turn_response, "chat_turn_1")
    
    # Test second message
    response2 = await chat.send_message("Second message")
    assert validate_response(response2, second_turn_response, "chat_turn_2")
    
    assert mock_chat.send_message_async.call_count == 2
    logger.info("Multi-turn chat test completed successfully")

@pytest.mark.asyncio
async def test_error_handling_mocked():
    """Test error handling with enhanced validation."""
    with patch('google.generativeai.GenerativeModel') as mock_model:
        # Set up mock to raise an exception
        mock_model.return_value.generate_content_async = AsyncMock(side_effect=Exception("API Error"))
        
        processor = GeminiSingleImage()
        
        # Log the start of error handling test
        logger.info("Testing error handling with mock API failure")
        
        with pytest.raises(RuntimeError) as exc_info:
            await processor.process_single_image(
                Image.new('RGB', (100, 100)),
                TEST_PROMPT
            )
        
        error_message = str(exc_info.value)
        assert "Failed to process image" in error_message
        logger.info(f"Error handling test completed successfully: {error_message}")

@pytest.mark.asyncio
async def test_retry_mechanism_mocked():
    """Test retry mechanism with enhanced validation."""
    with patch('google.generativeai.GenerativeModel') as mock_model:
        # Set up mock to fail twice then succeed
        mock_model.return_value.generate_content_async = AsyncMock(side_effect=[
            Exception("First failure"),
            Exception("Second failure"),
            MockResponse("Success after retries - The image shows...", "retry_test")
        ])
        
        processor = GeminiSingleImage()
        
        # Log retry attempts
        logger.info("Testing retry mechanism with mock failures")
        
        response = await processor.process_single_image(
            Image.new('RGB', (100, 100)),
            TEST_PROMPT
        )
        
        # Define expected format for retry response
        retry_response_format = {
            "length_range": (20, 500),
            "required_elements": ["Success", "retries"],
        }
        
        assert validate_response(response, retry_response_format, "retry_test")
        assert mock_model.return_value.generate_content_async.call_count == 3
        logger.info("Retry mechanism test completed successfully after 2 failures")

if __name__ == '__main__':
    pytest.main([__file__, '-v']) 