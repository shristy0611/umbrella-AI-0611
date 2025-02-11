"""Configuration module for Gemini API client."""

import os
import re
from typing import Optional, Dict, Any, List
import google.generativeai as genai
from dataclasses import dataclass
from enum import Enum
from .utils import logger, async_retry_with_backoff
from .secrets_manager import secrets_manager

class ServiceType(Enum):
    """Enum for different service types that use Gemini API."""
    OCR = "OCR"
    RECOMMENDATION = "RECOMMENDATION"
    SENTIMENT = "SENTIMENT"
    CHATBOT = "CHATBOT"
    ORCHESTRATOR = "ORCHESTRATOR"
    TASK_DECOMPOSER = "TASK_DECOMPOSER"
    RESULT_VERIFIER = "RESULT_VERIFIER"
    GENERAL = "GENERAL"

@dataclass
class GeminiConfig:
    """Configuration settings for Gemini API."""
    api_key: str
    service_type: ServiceType
    api_version: str = "v1alpha"
    max_retries: int = 3
    generation_config: Optional[Dict[str, Any]] = None
    safety_settings: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate_api_key()

    def validate_api_key(self) -> None:
        """Validate API key format and presence.
        
        Raises:
            ValueError: If API key is invalid
        """
        if not self.api_key:
            raise ValueError(f"API key for service {self.service_type.value} is not set")
        
        # Check if key matches expected format (AIza...)
        if not re.match(r'^AIza[0-9A-Za-z\-_]{35}$', self.api_key):
            raise ValueError(f"Invalid API key format for service {self.service_type.value}")

class GeminiClientConfig:
    """Singleton class to manage Gemini API client configuration."""
    _instance = None
    _is_initialized = False
    _logger = logger.getChild('config')
    _configs: Dict[ServiceType, GeminiConfig] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeminiClientConfig, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._is_initialized:
            self._load_all_configs()
            self._is_initialized = True

    def _load_all_configs(self) -> None:
        """Load configurations for all services."""
        # Get secrets from AWS Secrets Manager or environment variables
        secrets = secrets_manager.get_secrets()
        
        # Map secret keys to service types
        secret_mapping = {
            'ocr_api_key': ServiceType.OCR,
            'recommendation_api_key': ServiceType.RECOMMENDATION,
            'sentiment_api_key': ServiceType.SENTIMENT,
            'chatbot_api_key': ServiceType.CHATBOT,
            'orchestrator_api_key': ServiceType.ORCHESTRATOR,
            'task_decomposer_api_key': ServiceType.TASK_DECOMPOSER,
            'result_verifier_api_key': ServiceType.RESULT_VERIFIER,
            'default_api_key': ServiceType.GENERAL
        }

        for secret_key, service_type in secret_mapping.items():
            if secret_key in secrets:
                try:
                    config = GeminiConfig(
                        api_key=secrets[secret_key],
                        service_type=service_type,
                        api_version=os.getenv('GEMINI_API_VERSION', 'v1alpha'),
                        max_retries=int(os.getenv('GEMINI_MAX_RETRIES', '3')),
                        generation_config=self._get_default_generation_config(),
                        safety_settings=self._get_default_safety_settings()
                    )
                    self._configs[service_type] = config
                    self._logger.info(f"Loaded configuration for {service_type.value}")
                except ValueError as e:
                    self._logger.error(f"Failed to load config for {service_type.value}: {str(e)}")
                    raise

    @staticmethod
    def _get_default_generation_config() -> Dict[str, Any]:
        """Get default generation configuration."""
        return {
            "temperature": float(os.getenv('GEMINI_TEMPERATURE', '0.7')),
            "top_p": float(os.getenv('GEMINI_TOP_P', '0.8')),
            "top_k": int(os.getenv('GEMINI_TOP_K', '40')),
            "max_output_tokens": int(os.getenv('GEMINI_MAX_OUTPUT_TOKENS', '2048')),
        }

    @staticmethod
    def _get_default_safety_settings() -> Dict[str, str]:
        """Get default safety settings."""
        return {
            "HARM_CATEGORY_HARASSMENT": os.getenv('GEMINI_BLOCK_HARASSMENT', 'BLOCK_NONE'),
            "HARM_CATEGORY_HATE_SPEECH": os.getenv('GEMINI_BLOCK_HATE_SPEECH', 'BLOCK_NONE'),
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": os.getenv('GEMINI_BLOCK_EXPLICIT', 'BLOCK_NONE'),
            "HARM_CATEGORY_DANGEROUS_CONTENT": os.getenv('GEMINI_BLOCK_DANGEROUS', 'BLOCK_NONE')
        }

    def get_config(self, service_type: ServiceType) -> GeminiConfig:
        """Get configuration for a specific service.
        
        Args:
            service_type: Type of service requesting configuration
            
        Returns:
            GeminiConfig: Configuration for the specified service
            
        Raises:
            ValueError: If configuration for service type not found
        """
        if service_type not in self._configs:
            raise ValueError(f"No configuration found for service type {service_type.value}")
        return self._configs[service_type]

    @async_retry_with_backoff(max_retries=3, initial_delay=1)
    async def validate_api_key_with_request(self, service_type: ServiceType) -> bool:
        """Validate API key by making a test request.
        
        Args:
            service_type: Type of service to validate
            
        Returns:
            bool: True if key is valid, False otherwise
        """
        config = self.get_config(service_type)
        try:
            genai.configure(api_key=config.api_key)
            model = genai.GenerativeModel('gemini-pro')
            response = await model.generate_content("Test")
            return response is not None
        except Exception as e:
            self._logger.error(f"API key validation failed for {service_type.value}: {str(e)}")
            return False

    def get_client(self, service_type: ServiceType, model_name: Optional[str] = None) -> genai.GenerativeModel:
        """Get a configured Gemini API client for a specific service.
        
        Args:
            service_type: Type of service requesting client
            model_name: Optional model name to initialize with
            
        Returns:
            genai.GenerativeModel: Configured client instance
            
        Raises:
            RuntimeError: If client initialization fails
        """
        try:
            config = self.get_config(service_type)
            genai.configure(api_key=config.api_key)

            if model_name:
                client = genai.GenerativeModel(
                    model_name,
                    generation_config=config.generation_config,
                    safety_settings=config.safety_settings
                )
            else:
                client = None

            self._logger.info(
                f"Successfully configured Gemini client for {service_type.value} "
                f"(max_retries={config.max_retries})"
            )
            return client

        except Exception as e:
            self._logger.error(f"Failed to initialize Gemini client for {service_type.value}: {str(e)}")
            raise RuntimeError(f"Failed to initialize Gemini client: {str(e)}")

    def update_config(
        self,
        service_type: ServiceType,
        generation_config: Optional[Dict[str, Any]] = None,
        safety_settings: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update configuration settings for a specific service.
        
        Args:
            service_type: Type of service to update
            generation_config: Optional generation configuration
            safety_settings: Optional safety settings
        """
        config = self.get_config(service_type)
        
        if generation_config is not None:
            config.generation_config = generation_config
            self._logger.info(f"Updated generation configuration for {service_type.value}")

        if safety_settings is not None:
            config.safety_settings = safety_settings
            self._logger.info(f"Updated safety settings for {service_type.value}")

    def rotate_api_key(self, service_type: ServiceType) -> None:
        """Rotate API key for a specific service.
        
        Args:
            service_type: Type of service to rotate key for
            
        Raises:
            RuntimeError: If key rotation fails
        """
        try:
            # Get the secret key name for this service type
            secret_key = next(
                key for key, stype in {
                    'ocr_api_key': ServiceType.OCR,
                    'recommendation_api_key': ServiceType.RECOMMENDATION,
                    'sentiment_api_key': ServiceType.SENTIMENT,
                    'chatbot_api_key': ServiceType.CHATBOT,
                    'orchestrator_api_key': ServiceType.ORCHESTRATOR,
                    'task_decomposer_api_key': ServiceType.TASK_DECOMPOSER,
                    'result_verifier_api_key': ServiceType.RESULT_VERIFIER,
                    'default_api_key': ServiceType.GENERAL
                }.items() if stype == service_type
            )
            
            # Rotate the key in AWS Secrets Manager
            secrets_manager.rotate_keys(secret_key)
            
            # Reload configurations to get the new key
            self._load_all_configs()
            
            self._logger.info(f"Successfully rotated API key for {service_type.value}")
            
        except Exception as e:
            self._logger.error(f"Failed to rotate API key for {service_type.value}: {str(e)}")
            raise RuntimeError(f"Failed to rotate API key: {str(e)}")

# Global instance for easy access
gemini_config = GeminiClientConfig() 