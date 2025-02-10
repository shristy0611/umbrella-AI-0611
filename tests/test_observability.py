"""Tests for logging, tracing, and metrics collection functionality."""

import pytest
import json
import logging
import time
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from prometheus_client import REGISTRY
from shared.logging_config import setup_logging, log_with_context
from shared.middleware import setup_middleware

# Test FastAPI application
app = FastAPI()
setup_middleware(app, "test_service")

# Test endpoints
@app.get("/test_logging")
async def test_logging_endpoint(request: Request):
    logger = logging.getLogger(__name__)
    correlation_id = request.headers.get("X-Correlation-ID", "test-correlation-id")
    
    log_with_context(
        logger,
        logging.INFO,
        "Processing test request",
        correlation_id=correlation_id,
        extra={"endpoint": "/test_logging"}
    )
    return {"status": "success"}

@app.get("/test_error")
async def test_error_endpoint(request: Request):
    logger = logging.getLogger(__name__)
    correlation_id = request.headers.get("X-Correlation-ID", "test-correlation-id")
    
    try:
        raise ValueError("Test error")
    except Exception as e:
        log_with_context(
            logger,
            logging.ERROR,
            "Error in test endpoint",
            correlation_id=correlation_id,
            extra={"error": str(e)}
        )
        raise

@app.get("/test_tracing")
async def test_tracing_endpoint(request: Request):
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("test_operation") as span:
        span.set_attribute("test.attribute", "test_value")
        time.sleep(0.1)  # Simulate work
        return {"status": "success"}

# Test fixtures
@pytest.fixture
def setup_tracing():
    """Set up tracing for tests."""
    trace.set_tracer_provider(TracerProvider())
    trace.get_tracer_provider().add_span_processor(
        SimpleSpanProcessor(ConsoleSpanExporter())
    )
    yield
    # Clean up
    trace.get_tracer_provider().shutdown()

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

@pytest.fixture
def caplog(caplog):
    """Configure log capture."""
    caplog.set_level(logging.INFO)
    return caplog

def test_structured_logging(client, caplog):
    """Test structured logging with correlation ID."""
    correlation_id = "test-correlation-id"
    response = client.get(
        "/test_logging",
        headers={"X-Correlation-ID": correlation_id}
    )
    assert response.status_code == 200
    
    # Verify log contents
    for record in caplog.records:
        assert hasattr(record, "correlation_id")
        assert record.correlation_id == correlation_id
        assert "Processing test request" in record.message
        assert record.levelno == logging.INFO

def test_error_logging(client, caplog):
    """Test error logging and metrics."""
    correlation_id = "test-correlation-id"
    
    # Test endpoint that raises an error
    with pytest.raises(ValueError):
        client.get(
            "/test_error",
            headers={"X-Correlation-ID": correlation_id}
        )
    
    # Verify error was logged
    error_logs = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_logs) > 0
    assert "Error in test endpoint" in error_logs[0].message
    assert error_logs[0].correlation_id == correlation_id
    
    # Verify error metrics were incremented
    error_counter = REGISTRY.get_sample_value(
        'umbrella_errors_total',
        {'service': 'test_service', 'error_type': 'ValueError'}
    )
    assert error_counter > 0

def test_request_tracing(client, setup_tracing, caplog):
    """Test distributed tracing."""
    correlation_id = "test-correlation-id"
    response = client.get(
        "/test_tracing",
        headers={"X-Correlation-ID": correlation_id}
    )
    assert response.status_code == 200
    
    # Verify trace context in logs
    for record in caplog.records:
        assert hasattr(record, "correlation_id")
        assert hasattr(record, "trace_id")
        assert hasattr(record, "span_id")

def test_metrics_collection(client):
    """Test metrics collection."""
    # Make some requests to generate metrics
    endpoints = ["/test_logging", "/test_tracing"]
    for endpoint in endpoints:
        client.get(endpoint)
    
    # Get metrics
    response = client.get("/metrics")
    assert response.status_code == 200
    metrics_text = response.text
    
    # Verify key metrics are present
    assert 'umbrella_requests_total' in metrics_text
    assert 'umbrella_request_duration_seconds' in metrics_text
    
    # Verify metric values
    request_counter = REGISTRY.get_sample_value(
        'umbrella_requests_total',
        {'service': 'test_service', 'endpoint': '/test_logging', 'status': 'success'}
    )
    assert request_counter > 0

def test_correlation_propagation(client, caplog):
    """Test correlation ID propagation."""
    correlation_id = "test-correlation-id"
    
    # Make request with correlation ID
    response = client.get(
        "/test_logging",
        headers={"X-Correlation-ID": correlation_id}
    )
    assert response.status_code == 200
    
    # Verify correlation ID in response headers
    assert response.headers.get("X-Correlation-ID") == correlation_id
    
    # Verify correlation ID in logs
    for record in caplog.records:
        assert record.correlation_id == correlation_id

def test_trace_context_extraction(client, setup_tracing):
    """Test trace context extraction and propagation."""
    response = client.get("/test_tracing")
    assert response.status_code == 200
    
    # Verify trace headers in response
    assert "traceparent" in response.headers
    
    # Parse traceparent header
    traceparent = response.headers["traceparent"]
    assert traceparent.startswith("00-")  # Version
    assert len(traceparent.split("-")) == 4  # Format: version-trace_id-span_id-flags

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 