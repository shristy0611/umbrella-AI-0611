"""Shared logging configuration for UMBRELLA-AI."""

import logging
import json
import sys
import time
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger
from opentelemetry import trace
from prometheus_client import Counter, Histogram

# Initialize OpenTelemetry tracer
tracer = trace.get_tracer(__name__)

# Define Prometheus metrics
REQUEST_COUNTER = Counter(
    'umbrella_requests_total',
    'Total requests processed',
    ['service', 'endpoint', 'status']
)

LATENCY_HISTOGRAM = Histogram(
    'umbrella_request_duration_seconds',
    'Request duration in seconds',
    ['service', 'endpoint']
)

ERROR_COUNTER = Counter(
    'umbrella_errors_total',
    'Total errors encountered',
    ['service', 'error_type']
)

class CorrelationJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that includes correlation ID and trace info."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp if not present
        if not log_record.get('timestamp'):
            log_record['timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%S.%fZ', time.gmtime())
        
        # Add correlation ID from record
        if hasattr(record, 'correlation_id'):
            log_record['correlation_id'] = record.correlation_id
            
        # Add trace context if available
        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            log_record['trace_id'] = format(span_context.trace_id, '032x')
            log_record['span_id'] = format(span_context.span_id, '016x')

def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    log_file: Optional[str] = None
) -> None:
    """Set up logging configuration for a service.
    
    Args:
        service_name: Name of the service
        log_level: Logging level (default: INFO)
        log_file: Optional file to write logs to
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Create formatter
    formatter = CorrelationJsonFormatter(
        fmt='%(timestamp)s %(level)s %(name)s %(correlation_id)s %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Add service name to all log records
    logger = logging.LoggerAdapter(logger, {'service': service_name})
    
    logger.info(f"Logging initialized for service: {service_name}")

def log_with_context(
    logger: logging.Logger,
    level: int,
    msg: str,
    correlation_id: Optional[str] = None,
    **kwargs: Any
) -> None:
    """Log a message with correlation ID and additional context.
    
    Args:
        logger: Logger instance
        level: Logging level
        msg: Log message
        correlation_id: Optional correlation ID
        **kwargs: Additional context to include in log
    """
    extra = kwargs.pop('extra', {})
    if correlation_id:
        extra['correlation_id'] = correlation_id
    
    # Add trace context
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        extra['trace_id'] = format(span_context.trace_id, '032x')
        extra['span_id'] = format(span_context.span_id, '016x')
    
    logger.log(level, msg, extra=extra, **kwargs)

def increment_request_counter(service: str, endpoint: str, status: str) -> None:
    """Increment the request counter metric.
    
    Args:
        service: Service name
        endpoint: API endpoint
        status: Request status (success/error)
    """
    REQUEST_COUNTER.labels(service=service, endpoint=endpoint, status=status).inc()

def observe_request_duration(service: str, endpoint: str, duration: float) -> None:
    """Record request duration in the histogram metric.
    
    Args:
        service: Service name
        endpoint: API endpoint
        duration: Request duration in seconds
    """
    LATENCY_HISTOGRAM.labels(service=service, endpoint=endpoint).observe(duration)

def increment_error_counter(service: str, error_type: str) -> None:
    """Increment the error counter metric.
    
    Args:
        service: Service name
        error_type: Type of error encountered
    """
    ERROR_COUNTER.labels(service=service, error_type=error_type).inc() 