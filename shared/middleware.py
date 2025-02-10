from starlette.types import ASGIApp
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
import uuid
from .logging_utils import correlation_id_context, setup_logger
import time
from typing import Callable, Dict, Any
from fastapi import Request, Response
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
import logging
from .logging_config import (
    increment_request_counter,
    observe_request_duration,
    increment_error_counter,
    log_with_context
)

logger = setup_logger('middleware')
tracer = trace.get_tracer(__name__)

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation IDs for request tracing."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())
        
        # Set correlation ID in context
        token = correlation_id_context.set(correlation_id)
        
        try:
            logger.info("Processing request", extra={"path": request.url.path, "method": request.method})
            # Call next middleware/endpoint
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers['X-Correlation-ID'] = correlation_id
            
            return response
        except Exception as e:
            logger.error("Error processing request: %s", str(e), exc_info=True)
            raise
        finally:
            # Reset correlation ID context
            correlation_id_context.reset(token)
            logger.info("Finished processing request", extra={"path": request.url.path, "method": request.method})

class TracingMiddleware:
    """Middleware for distributed tracing using OpenTelemetry."""
    
    def __init__(self, app: Any, service_name: str):
        """Initialize the middleware.
        
        Args:
            app: FastAPI application
            service_name: Name of the service
        """
        self.app = app
        self.service_name = service_name
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process the request with tracing.
        
        Args:
            request: FastAPI request
            call_next: Next middleware in chain
            
        Returns:
            Response from the next middleware
        """
        start_time = time.time()
        correlation_id = request.headers.get("X-Correlation-ID", "unknown")
        method = request.method
        path = request.url.path
        
        with tracer.start_as_current_span(
            name=f"{method} {path}",
            attributes={
                "service.name": self.service_name,
                "http.method": method,
                "http.url": str(request.url),
                "correlation_id": correlation_id
            }
        ) as span:
            try:
                # Process request
                response = await call_next(request)
                duration = time.time() - start_time
                
                # Record metrics
                increment_request_counter(
                    self.service_name,
                    path,
                    "success" if response.status_code < 400 else "error"
                )
                observe_request_duration(self.service_name, path, duration)
                
                # Update span
                span.set_status(Status(StatusCode.OK))
                span.set_attribute("http.status_code", response.status_code)
                
                # Log request completion
                log_with_context(
                    logger,
                    logging.INFO,
                    f"Request completed: {method} {path}",
                    correlation_id=correlation_id,
                    extra={
                        "duration": duration,
                        "status_code": response.status_code
                    }
                )
                
                return response
                
            except Exception as e:
                # Record error metrics
                increment_error_counter(self.service_name, type(e).__name__)
                
                # Update span with error details
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                
                # Log error
                log_with_context(
                    logger,
                    logging.ERROR,
                    f"Request failed: {method} {path}",
                    correlation_id=correlation_id,
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                
                raise

class MetricsMiddleware:
    """Middleware for collecting and exposing Prometheus metrics."""
    
    def __init__(self, app: Any):
        """Initialize the middleware.
        
        Args:
            app: FastAPI application
        """
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process the request and collect metrics.
        
        Args:
            request: FastAPI request
            call_next: Next middleware in chain
            
        Returns:
            Response from the next middleware
        """
        # Handle metrics endpoint
        if request.url.path == "/metrics":
            return Response(
                generate_latest(),
                media_type=CONTENT_TYPE_LATEST
            )
        
        # Process normal request
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Ensure metrics are recorded even if request fails
            increment_error_counter(
                request.app.state.service_name,
                type(e).__name__
            )
            raise

def setup_middleware(app: Any, service_name: str) -> None:
    """Set up all middleware for an application.
    
    Args:
        app: FastAPI application
        service_name: Name of the service
    """
    # Store service name in app state
    app.state.service_name = service_name
    
    # Add middleware in reverse order (last added = first executed)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(TracingMiddleware, service_name=service_name) 