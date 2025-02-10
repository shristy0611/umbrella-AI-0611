"""Integration tests for Gemini API modules."""

import os
import asyncio
import pytest
from PIL import Image
from io import BytesIO
import requests
from shared.gemini import (
    GeminiTextChat,
    GeminiSingleImage,
    GeminiMultiImage,
    GeminiFileUpload,
    GeminiMultiTurnChat,
    gemini_config
)

# Test data
TEST_IMAGE_URL = "https://raw.githubusercontent.com/google/generative-ai-python/main/examples/image.jpg"
TEST_PROMPT = "What do you see in this image?"
TEST_CHAT_PROMPT = "Tell me a short story about a robot learning to paint."
TEST_CONTEXT = "You are an art critic reviewing paintings."

@pytest.fixture
def setup_env():
    """Set up test environment."""
    # Save original environment
    original_env = {}
    if 'GEMINI_API_KEY' in os.environ:
        original_env['GEMINI_API_KEY'] = os.environ['GEMINI_API_KEY']

    # Set test environment
    os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', 'test_key')
    
    yield

    # Restore original environment
    for key, value in original_env.items():
        os.environ[key] = value

@pytest.fixture
def test_image():
    """Get a test image."""
    response = requests.get(TEST_IMAGE_URL)
    return Image.open(BytesIO(response.content))

@pytest.mark.asyncio
async def test_text_chat(setup_env):
    """Test text chat functionality."""
    chat = GeminiTextChat()
    
    # Start chat session
    await chat.start_text_chat()
    assert chat.chat is not None
    
    # Send message
    response = await chat.send_message(TEST_CHAT_PROMPT)
    assert response is not None
    assert hasattr(response, 'text')
    print(f"\nText Chat Response:\n{response.text}\n")
    
    # Check chat history
    history = chat.get_chat_history()
    assert isinstance(history, list)
    assert len(history) > 0

@pytest.mark.asyncio
async def test_single_image(setup_env, test_image):
    """Test single image processing."""
    image_processor = GeminiSingleImage()
    
    # Process image
    response = await image_processor.process_single_image(test_image, TEST_PROMPT)
    assert response is not None
    assert hasattr(response, 'text')
    print(f"\nSingle Image Response:\n{response.text}\n")

@pytest.mark.asyncio
async def test_multiple_images(setup_env, test_image):
    """Test multiple image processing."""
    image_processor = GeminiMultiImage()
    
    # Create list of test images
    images = [test_image, test_image]  # Using same image twice for testing
    
    # Process images
    response = await image_processor.process_multiple_images(images, "Compare these images")
    assert response is not None
    assert hasattr(response, 'text')
    print(f"\nMultiple Images Response:\n{response.text}\n")

@pytest.mark.asyncio
async def test_file_upload(setup_env, test_image):
    """Test file upload and processing."""
    file_processor = GeminiFileUpload()
    
    # Save test image to temporary file
    test_image_path = "tests/data/test_image.jpg"
    test_image.save(test_image_path)
    
    try:
        # Process file
        response = await file_processor.process_file(
            test_image_path,
            TEST_PROMPT,
            mime_type="image/jpeg"
        )
        assert response is not None
        assert hasattr(response, 'text')
        print(f"\nFile Upload Response:\n{response.text}\n")
    finally:
        # Clean up
        if os.path.exists(test_image_path):
            os.remove(test_image_path)

@pytest.mark.asyncio
async def test_multi_turn_chat(setup_env):
    """Test multi-turn chat functionality."""
    chat = GeminiMultiTurnChat()
    
    # Start chat session with context
    await chat.start_chat_session(TEST_CONTEXT)
    assert chat.chat is not None
    assert chat.get_context() == TEST_CONTEXT
    
    # Send first message
    response1 = await chat.send_message("Describe a modern abstract painting.")
    assert response1 is not None
    assert hasattr(response1, 'text')
    print(f"\nMulti-turn Chat Response 1:\n{response1.text}\n")
    
    # Send follow-up message
    response2 = await chat.send_message("What emotions does it evoke?")
    assert response2 is not None
    assert hasattr(response2, 'text')
    print(f"\nMulti-turn Chat Response 2:\n{response2.text}\n")
    
    # Check chat history
    history = chat.get_chat_history()
    assert isinstance(history, list)
    assert len(history) > 0
    
    # Update context
    new_context = "You are now a modern art curator."
    await chat.update_context(new_context)
    assert chat.get_context() == new_context

@pytest.mark.asyncio
async def test_client_configuration(setup_env):
    """Test client configuration updates."""
    # Update configuration
    generation_config = {
        'temperature': 0.9,
        'top_p': 0.8,
        'top_k': 40
    }
    safety_settings = {
        "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
        "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
        "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"
    }
    
    gemini_config.update_config(
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    
    # Get client with updated config
    client = gemini_config.get_client('models/gemini-pro')
    assert client is not None
    assert client.model_name == 'models/gemini-pro'

if __name__ == '__main__':
    pytest.main([__file__, '-v']) 