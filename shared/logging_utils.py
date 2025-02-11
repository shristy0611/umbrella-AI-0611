import logging
import uuid
from contextvars import ContextVar
from functools import wraps
from typing import Optional

# Context variable to store correlation ID
correlation_id_context: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIdFilter(logging.Filter):
    """Filter that adds correlation_id to log records."""

    def filter(self, record):
        record.correlation_id = correlation_id_context.get("")
        return True


def setup_logger(service_name: str, log_level: str = "INFO") -> logging.Logger:
    """
    Set up a logger with correlation ID support for a service.

    Args:
        service_name: Name of the service (e.g., 'orchestrator', 'pdf_service')
        log_level: Logging level (default: 'INFO')

    Returns:
        Logger instance configured with correlation ID support
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(getattr(logging, log_level.upper()))

    # Create formatter with correlation ID
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - [correlation_id=%(correlation_id)s] - %(levelname)s - %(message)s"
    )

    # Add correlation ID filter and formatter to handler
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


def with_correlation_id(func):
    """
    Decorator to ensure a correlation ID is set for the function execution.
    If no correlation ID is provided, generates a new one.
    """

    @wraps(func)
    async def wrapper(*args, correlation_id: Optional[str] = None, **kwargs):
        # Generate or use provided correlation ID
        cid = correlation_id or str(uuid.uuid4())
        token = correlation_id_context.set(cid)
        try:
            return await func(*args, correlation_id=cid, **kwargs)
        finally:
            correlation_id_context.reset(token)

    return wrapper


def get_correlation_id() -> str:
    """Get the current correlation ID from context."""
    return correlation_id_context.get("")
