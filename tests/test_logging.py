"""Tests for logging, tracing, and metrics collection."""

import pytest
import logging
import json
import time
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from prometheus_client import REGISTRY
from shared.logging_config import setup_logging, log_with_context
from shared.middleware import setup_middleware

# Set up test application
app = FastAPI()
setup_middleware(app, "test_service")

@app.get("/test")
async def test_endpoint():
    return {"message": "Test endpoint"}

@app.get("/error")
async def error_endpoint():
    raise ValueError("Test error")

@pytest.fixture
def setup_tracing():
    """Set up OpenTelemetry tracing for tests."""
    # Configure tracer
    provider = TracerProvider()
    processor = SimpleSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    
    return provider

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

@pytest.fixture
def caplog(caplog):
    """Configure caplog for JSON logging."""
    caplog.set_level(logging.INFO)
    return caplog

def test_request_logging(client, caplog):
    """Test that requests are properly logged."""
    # Make test request
    response = client.get("/test", headers={"X-Correlation-ID": "test-123"})
    assert response.status_code == 200
    
    # Check logs
    assert len(caplog.records) > 0
    
    # Find request log
    request_log = None
    for record in caplog.records:
        if "Request completed" in record.message:
            request_log = record
            break
    
    assert request_log is not None
    assert request_log.correlation_id == "test-123"
    assert "duration" in request_log.__dict__
    assert "status_code" in request_log.__dict__

def test_error_logging(client, caplog):
    """Test that errors are properly logged."""
    # Make request that will cause error
    with pytest.raises(ValueError):
        client.get("/error", headers={"X-Correlation-ID": "test-456"})
    
    # Check logs
    assert len(caplog.records) > 0
    
    # Find error log
    error_log = None
    for record in caplog.records:
        if "Request failed" in record.message:
            error_log = record
            break
    
    assert error_log is not None
    assert error_log.correlation_id == "test-456"
    assert "error" in error_log.__dict__
    assert "error_type" in error_log.__dict__
    assert error_log.__dict__["error_type"] == "ValueError"

def test_tracing(client, setup_tracing):
    """Test that distributed tracing is working."""
    # Make test request
    response = client.get("/test", headers={
        "X-Correlation-ID": "test-789",
        "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
    })
    assert response.status_code == 200
    
    # Get current span and check attributes
    span = trace.get_current_span()
    assert span.get_span_context().is_valid
    
    # Verify span attributes
    attributes = span.get_attributes()
    assert attributes["service.name"] == "test_service"
    assert attributes["http.method"] == "GET"
    assert attributes["correlation_id"] == "test-789"

def test_metrics_endpoint(client):
    """Test that metrics endpoint is working."""
    # Make some test requests to generate metrics
    client.get("/test")
    try:
        client.get("/error")
    except ValueError:
        pass
    
    # Get metrics
    response = client.get("/metrics")
    assert response.status_code == 200
    
    # Check metric presence
    metrics_text = response.text
    assert 'umbrella_requests_total' in metrics_text
    assert 'umbrella_request_duration_seconds' in metrics_text
    assert 'umbrella_errors_total' in metrics_text

def test_metrics_collection():
    """Test that metrics are being collected correctly."""
    # Get current values
    requests_total = REGISTRY.get_sample_value(
        'umbrella_requests_total_total',
        {'service': 'test_service', 'endpoint': '/test', 'status': 'success'}
    )
    errors_total = REGISTRY.get_sample_value(
        'umbrella_errors_total_total',
        {'service': 'test_service', 'error_type': 'ValueError'}
    )
    
    assert requests_total is not None
    assert errors_total is not None

def test_structured_logging(caplog):
    """Test that logs are properly structured in JSON format."""
    logger = logging.getLogger("test_logger")
    setup_logging("test_service")
    
    # Log test message
    log_with_context(
        logger,
        logging.INFO,
        "Test message",
        correlation_id="test-abc",
        extra={"custom_field": "test_value"}
    )
    
    # Check log record
    assert len(caplog.records) > 0
    record = caplog.records[-1]
    
    # Verify log structure
    assert record.correlation_id == "test-abc"
    assert "custom_field" in record.__dict__
    assert record.__dict__["custom_field"] == "test_value"
    
    # Verify JSON formatting
    log_message = record.__dict__
    assert "timestamp" in log_message
    assert "level" in log_message
    assert "correlation_id" in log_message

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 