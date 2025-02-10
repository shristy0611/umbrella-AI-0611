"""Logging utilities for the UMBRELLA-AI system."""

import logging
import json
import uuid
from typing import Optional, Dict, Any
from pythonjsonlogger import jsonlogger
from contextvars import ContextVar
from functools import wraps
import asyncio

# Context variable to store correlation ID
correlation_id_context: ContextVar[str] = ContextVar('correlation_id', default='')

class CorrelationIdFilter(logging.Filter):
    """Filter that adds correlation ID to log records."""
    
    def filter(self, record):
        """Add correlation ID to the log record."""
        record.correlation_id = correlation_id_context.get('')
        return True

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for logs."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record['timestamp'] = self.formatTime(record)
        log_record['level'] = record.levelname
        log_record['correlation_id'] = getattr(record, 'correlation_id', '')
        log_record['service'] = getattr(record, 'service', '')
        
        # Add extra fields from record
        if hasattr(record, 'extra'):
            for key, value in record.extra.items():
                log_record[key] = value

def setup_logging(service_name: str, log_level: str = 'INFO') -> None:
    """Set up logging configuration for a service.
    
    Args:
        service_name: Name of the service
        log_level: Logging level (default: INFO)
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(correlation_id)s %(message)s'
    )
    
    # Add correlation ID filter
    console_handler.addFilter(CorrelationIdFilter())
    
    # Set formatter
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Set service name as a default field
    logger = logging.LoggerAdapter(logger, {'service': service_name})
    
    return logger

def get_correlation_id() -> str:
    """Get the current correlation ID."""
    return correlation_id_context.get('')

def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set a new correlation ID in the context.
    
    Args:
        correlation_id: Optional correlation ID to set. If None, generates a new one.
    
    Returns:
        The set correlation ID
    """
    cid = correlation_id or str(uuid.uuid4())
    correlation_id_context.set(cid)
    return cid

def with_correlation_id(func):
    """Decorator to ensure a correlation ID is set for a function."""
    
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        # Get existing correlation ID or generate new one
        cid = get_correlation_id() or set_correlation_id()
        
        try:
            return await func(*args, **kwargs)
        finally:
            # Reset correlation ID if we set a new one
            if not get_correlation_id():
                correlation_id_context.set('')
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        # Get existing correlation ID or generate new one
        cid = get_correlation_id() or set_correlation_id()
        
        try:
            return func(*args, **kwargs)
        finally:
            # Reset correlation ID if we set a new one
            if not get_correlation_id():
                correlation_id_context.set('')
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper 