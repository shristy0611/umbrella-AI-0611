"""Configuration module for Gemini API client."""

import os
from typing import Optional, Dict, Any
import google.generativeai as genai
from dataclasses import dataclass
from .utils import logger

@dataclass
class GeminiConfig:
    """Configuration settings for Gemini API."""
    api_key: str
    api_version: str = "v1alpha"
    max_retries: int = 3
    generation_config: Optional[Dict[str, Any]] = None
    safety_settings: Optional[Dict[str, Any]] = None

class GeminiClientConfig:
    """Singleton class to manage Gemini API client configuration."""
    _instance = None
    _is_initialized = False
    _logger = logger.getChild('config')

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeminiClientConfig, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._is_initialized:
            self._config = self._load_config()
            self._is_initialized = True

    @staticmethod
    def _load_config() -> GeminiConfig:
        """Load configuration from environment variables.
        
        Returns:
            GeminiConfig: Configuration object
            
        Raises:
            ValueError: If required environment variables are missing
        """
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        # Optional configurations with defaults
        api_version = os.getenv('GEMINI_API_VERSION', 'v1alpha')
        max_retries = int(os.getenv('GEMINI_MAX_RETRIES', '3'))

        # Default generation config
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 2048,
        }

        # Default safety settings using HarmCategory and HarmBlockThreshold enums
        safety_settings = {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"
        }

        return GeminiConfig(
            api_key=api_key,
            api_version=api_version,
            max_retries=max_retries,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

    def get_client(self, model_name: Optional[str] = None) -> genai.GenerativeModel:
        """Get a configured Gemini API client.
        
        Args:
            model_name: Optional model name to initialize with
            
        Returns:
            genai.GenerativeModel: Configured client instance
            
        Raises:
            RuntimeError: If client initialization fails
        """
        try:
            # Configure the client
            genai.configure(api_key=self._config.api_key)

            # Create model instance if model name provided
            if model_name:
                client = genai.GenerativeModel(
                    model_name,
                    generation_config=self._config.generation_config,
                    safety_settings=self._config.safety_settings
                )
            else:
                client = None

            self._logger.info(
                f"Successfully configured Gemini client "
                f"(max_retries={self._config.max_retries})"
            )
            return client

        except Exception as e:
            self._logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise RuntimeError(f"Failed to initialize Gemini client: {str(e)}")

    def update_config(
        self,
        generation_config: Optional[Dict[str, Any]] = None,
        safety_settings: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update configuration settings.
        
        Args:
            generation_config: Optional generation configuration
            safety_settings: Optional safety settings
        """
        if generation_config is not None:
            self._config.generation_config = generation_config
            self._logger.info("Updated generation configuration")

        if safety_settings is not None:
            self._config.safety_settings = safety_settings
            self._logger.info("Updated safety settings")

# Global instance for easy access
gemini_config = GeminiClientConfig() 