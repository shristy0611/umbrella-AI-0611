"""Shared configuration for Gemini models."""

import os
import logging
import google.generativeai as genai
from typing import Optional

logger = logging.getLogger(__name__)

class GeminiConfig:
    """Configuration for Gemini models."""

    @staticmethod
    def configure_model(service_type: str) -> genai.GenerativeModel:
        """Configure and return a Gemini model for a specific service.
        
        Args:
            service_type: Type of service (OCR, RECOMMENDATION, SENTIMENT, CHATBOT, etc.)
            
        Returns:
            genai.GenerativeModel: Configured Gemini model
        """
        # Get API key for service
        api_key = os.getenv(f"GEMINI_API_KEY_{service_type.upper()}")
        if not api_key:
            raise ValueError(f"Missing API key for service: {service_type}")

        # Get model name from environment
        model_name = os.getenv(f"GEMINI_MODEL_{service_type.upper()}")
        if not model_name:
            # Default to flash-exp for basic services and flash-thinking-exp for complex tasks
            if service_type in ["ORCHESTRATOR", "TASK_DECOMPOSER", "RESULT_VERIFIER"]:
                model_name = "gemini-2.0-flash-thinking-exp"
            else:
                model_name = "gemini-2.0-flash-exp"

        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        logger.info(f"Configured {service_type} service with model: {model_name}")
        return model

    @staticmethod
    def get_generation_config(service_type: str) -> dict:
        """Get generation configuration for a service.
        
        Args:
            service_type: Type of service
            
        Returns:
            dict: Generation configuration
        """
        return {
            "temperature": float(os.getenv("GEMINI_TEMPERATURE", "0.1")),
            "top_p": float(os.getenv("GEMINI_TOP_P", "0.8")),
            "top_k": int(os.getenv("GEMINI_TOP_K", "40")),
            "max_output_tokens": int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "2048")),
        }

# Global instance
gemini_config = GeminiConfig() 