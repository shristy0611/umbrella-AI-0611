from starlette.types import ASGIApp
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
import uuid
from .logging_utils import correlation_id_context, setup_logger
import time
from typing import Callable, Dict, Any
from fastapi import Request, Response, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest, Counter, Histogram, CollectorRegistry
import logging
from .logging_config import (
    increment_request_counter,
    observe_request_duration,
    increment_error_counter,
    log_with_context
)

logger = setup_logger('middleware')
tracer = trace.get_tracer(__name__)

# Create a custom registry for our metrics
REGISTRY = CollectorRegistry()

# Metrics
REQUEST_COUNT = Counter(
    'umbrella_requests_total',
    'Total number of requests',
    ['service', 'endpoint', 'method', 'status'],
    registry=REGISTRY
)

REQUEST_LATENCY = Histogram(
    'umbrella_request_latency_seconds',
    'Request latency in seconds',
    ['service', 'endpoint'],
    registry=REGISTRY
)

ERROR_COUNTER = Counter(
    'umbrella_errors_total',
    'Total number of errors',
    ['service', 'error_type'],
    registry=REGISTRY
)

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

class AuthMiddleware:
    """Middleware for handling authentication."""
    
    def __init__(
        self,
        app: Any,
        secret_key: str,
        algorithm: str = "HS256",
        exclude_paths: list = None
    ):
        """Initialize the middleware.
        
        Args:
            app: FastAPI application
            secret_key: JWT secret key
            algorithm: JWT algorithm
            exclude_paths: Paths to exclude from authentication
        """
        self.app = app
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
        self.security = HTTPBearer()
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process the request.
        
        Args:
            request: FastAPI request
            call_next: Next middleware in chain
            
        Returns:
            Response from the next middleware
            
        Raises:
            HTTPException: If authentication fails
        """
        # Skip authentication for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        try:
            # Get token from header
            credentials: HTTPAuthorizationCredentials = await self.security(request)
            token = credentials.credentials
            
            # Validate token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Add user info to request state
            request.state.user = payload
            
            return await call_next(request)
            
        except JWTError as e:
            logger.warning(f"JWT validation failed: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials"
            )
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(
                status_code=403,
                detail="Could not validate credentials"
            )

class RateLimitMiddleware:
    """Middleware for rate limiting requests."""
    
    def __init__(
        self,
        app: Any,
        requests_per_minute: int = 60,
        burst_limit: int = 10
    ):
        """Initialize the middleware.
        
        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests per minute
            burst_limit: Maximum burst of requests
        """
        self.app = app
        self.rate_limit = requests_per_minute
        self.burst_limit = burst_limit
        self.requests: Dict[str, list] = {}
    
    def _clean_old_requests(self, client_id: str):
        """Clean old requests for a client."""
        now = time.time()
        self.requests[client_id] = [
            ts for ts in self.requests[client_id]
            if now - ts < 60  # Keep requests from last minute
        ]
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process the request.
        
        Args:
            request: FastAPI request
            call_next: Next middleware in chain
            
        Returns:
            Response from the next middleware
            
        Raises:
            HTTPException: If rate limit is exceeded
        """
        # Get client identifier (IP or user ID)
        client_id = request.client.host
        if hasattr(request.state, "user"):
            client_id = request.state.user.get("sub", client_id)
        
        # Initialize request tracking for new clients
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Clean old requests
        self._clean_old_requests(client_id)
        
        # Check rate limit
        if len(self.requests[client_id]) >= self.rate_limit:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )
        
        # Check burst limit
        now = time.time()
        recent_requests = len([
            ts for ts in self.requests[client_id]
            if now - ts < 1  # Requests in last second
        ])
        if recent_requests >= self.burst_limit:
            logger.warning(f"Burst limit exceeded for client: {client_id}")
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )
        
        # Track request
        self.requests[client_id].append(now)
        
        return await call_next(request)

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
        
        # Start timing
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Record metrics
            REQUEST_COUNT.labels(
                service=request.app.state.service_name,
                endpoint=request.url.path,
                method=request.method,
                status=response.status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                service=request.app.state.service_name,
                endpoint=request.url.path
            ).observe(time.time() - start_time)
            
            return response
            
        except Exception as e:
            # Record error metrics
            ERROR_COUNTER.labels(
                service=request.app.state.service_name,
                error_type=type(e).__name__
            ).inc()
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