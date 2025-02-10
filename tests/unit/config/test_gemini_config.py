"""Test module for Gemini API configuration."""

import os
import pytest
from shared.gemini.config import gemini_config, GeminiClientConfig
import google.generativeai as genai

@pytest.fixture
def setup_env():
    """Set up test environment variables."""
    original_env = {}
    if 'GEMINI_API_KEY' in os.environ:
        original_env['GEMINI_API_KEY'] = os.environ['GEMINI_API_KEY']
    os.environ['GEMINI_API_KEY'] = 'test_key'
    yield
    # Restore original environment
    if original_env:
        os.environ['GEMINI_API_KEY'] = original_env['GEMINI_API_KEY']
    else:
        del os.environ['GEMINI_API_KEY']

def test_singleton_pattern():
    """Test that GeminiClientConfig follows singleton pattern."""
    config1 = GeminiClientConfig()
    config2 = GeminiClientConfig()
    assert config1 is config2

def test_missing_api_key():
    """Test that missing API key raises ValueError."""
    if 'GEMINI_API_KEY' in os.environ:
        del os.environ['GEMINI_API_KEY']
    
    with pytest.raises(ValueError) as exc_info:
        GeminiClientConfig()._load_config()  # Call _load_config directly
    assert "GEMINI_API_KEY environment variable not set" in str(exc_info.value)

def test_config_initialization(setup_env):
    """Test configuration initialization with environment variables."""
    config = GeminiClientConfig()
    assert config._config.api_version == 'v1alpha'
    assert config._config.max_retries == 3  # Default value is 3

def test_get_client(setup_env):
    """Test getting a configured client."""
    client = gemini_config.get_client('gemini-pro')
    assert isinstance(client, genai.GenerativeModel)
    assert client.model_name == 'models/gemini-pro'  # Full model name includes 'models/' prefix

def test_update_config(setup_env):
    """Test updating configuration settings."""
    generation_config = {
        'temperature': 0.9,
        'top_p': 0.8
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
    
    assert gemini_config._config.generation_config == generation_config
    assert gemini_config._config.safety_settings == safety_settings

if __name__ == '__main__':
    pytest.main([__file__, '-v']) 