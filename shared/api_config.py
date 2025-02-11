"""API configuration module for managing service configurations and API settings."""

import os
from typing import Dict, Any, List
from pydantic_settings import BaseSettings


class APIConfig(BaseSettings):
    # API Keys
    GEMINI_API_KEY_OCR: str = ""
    GEMINI_API_KEY_RECOMMENDATION: str = ""
    GEMINI_API_KEY_SENTIMENT: str = ""
    GEMINI_API_KEY_CHATBOT: str = ""
    ORCHESTRATOR_API_KEY: str = ""
    TASK_DECOMPOSER_API_KEY: str = ""
    RESULT_VERIFIER_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Gemini API Configuration
    GEMINI_API_VERSION: str = "v1alpha"
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_TEMPERATURE: float = 0.1
    GEMINI_TOP_P: float = 0.8
    GEMINI_TOP_K: int = 40
    GEMINI_MAX_OUTPUT_TOKENS: int = 2048
    GEMINI_BLOCK_HARASSMENT: str = "BLOCK_NONE"
    GEMINI_BLOCK_HATE_SPEECH: str = "BLOCK_NONE"
    GEMINI_BLOCK_EXPLICIT: str = "BLOCK_NONE"
    GEMINI_BLOCK_DANGEROUS: str = "BLOCK_NONE"

    # Database Configuration
    MONGODB_URI: str = "mongodb://mongodb:27017/umbrella"
    VECTOR_DB_PATH: str = "./data/vector_db"
    VECTOR_DB_URL: str = "http://vector_db:8005"

    # AWS Configuration
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = ""

    # Cache and Message Queue Configuration
    REDIS_URL: str = "redis://redis:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"

    # Model Configuration
    SENTIMENT_MODEL: str = "distilbert-base-uncased-finetuned-sst-2-english"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Application Configuration
    LOG_LEVEL: str = "DEBUG"
    ENVIRONMENT: str = "development"
    REDIS_CACHE_TTL: int = 3600
    VECTOR_CACHE_SIZE: int = 10000

    # RabbitMQ Configuration
    RABBITMQ_QUEUE: str = "tasks"
    RABBITMQ_EXCHANGE: str = "umbrella_ai"
    RABBITMQ_ROUTING_KEY: str = "task.process"

    # OpenTelemetry Configuration
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://otel-collector:4317"

    # Testing Configuration
    PYTEST_ADDOPTS: str = (
        "--html=test-reports/report.html --cov=src --cov-report=html:test-reports/coverage"
    )

    # Service Ports
    PDF_EXTRACTION_PORT: int = 8001
    SENTIMENT_ANALYSIS_PORT: int = 8002
    RAG_SCRAPER_PORT: int = 8003
    CHATBOT_PORT: int = 8004
    API_GATEWAY_PORT: int = 8000

    # Service URLs
    PDF_SERVICE_URL: str = "http://pdf_service:8001"
    SENTIMENT_SERVICE_URL: str = "http://sentiment_service:8002"
    CHATBOT_SERVICE_URL: str = "http://chatbot_service:8003"
    SCRAPER_SERVICE_URL: str = "http://scraper_service:8004"

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_DEBUG: bool = False

    # Security Configuration
    JWT_SECRET_KEY: str = "your_development_jwt_secret_key_here"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Logging Configuration
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # File Upload Configuration (10MB in bytes)
    MAX_UPLOAD_SIZE: int = 10485760
    ALLOWED_FILE_TYPES: str = ".pdf,.txt,.doc,.docx"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    BURST_LIMIT: int = 10

    # Service Configuration
    MAX_RETRIES: int = 3
    TIMEOUT_SECONDS: int = 30
    BATCH_SIZE: int = 10

    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # Development Settings
    DEBUG: bool = False
    TESTING: bool = False
    RELOAD: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

    def get_service_url(self, service_name: str) -> str:
        """Get the URL for a specific service.

        Args:
            service_name: Name of the service

        Returns:
            str: Service URL

        Raises:
            ValueError: If service name is invalid
        """
        service_urls = {
            "pdf": self.PDF_SERVICE_URL,
            "sentiment": self.SENTIMENT_SERVICE_URL,
            "chatbot": self.CHATBOT_SERVICE_URL,
            "scraper": self.SCRAPER_SERVICE_URL,
            "vector_db": self.VECTOR_DB_URL,
        }

        if service_name not in service_urls:
            raise ValueError(f"Invalid service name: {service_name}")

        return service_urls[service_name]

    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get configuration for a specific service.

        Args:
            service_name: Name of the service

        Returns:
            Dict[str, Any]: Service configuration

        Raises:
            ValueError: If service name is invalid
        """
        base_config = {
            "max_retries": self.MAX_RETRIES,
            "timeout": self.TIMEOUT_SECONDS,
            "batch_size": self.BATCH_SIZE,
        }

        service_configs = {
            "pdf": {"url": self.PDF_SERVICE_URL, **base_config},
            "sentiment": {"url": self.SENTIMENT_SERVICE_URL, **base_config},
            "chatbot": {"url": self.CHATBOT_SERVICE_URL, **base_config},
            "scraper": {"url": self.SCRAPER_SERVICE_URL, **base_config},
            "vector_db": {"url": self.VECTOR_DB_URL, **base_config},
        }

        if service_name not in service_configs:
            raise ValueError(f"Invalid service name: {service_name}")

        return service_configs[service_name]


api_config = APIConfig()
