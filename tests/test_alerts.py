"""Tests for alert system functionality."""

import pytest
import requests
import time
from prometheus_client import Counter, Gauge, Histogram
from shared.logging_config import (
    REQUEST_COUNTER,
    LATENCY_HISTOGRAM,
    ERROR_COUNTER
)

# Test metrics
TEST_ERROR_COUNTER = Counter(
    'test_errors_total',
    'Total test errors',
    ['service', 'test_type']
)

TEST_LATENCY = Histogram(
    'test_duration_seconds',
    'Test duration in seconds',
    ['service', 'test_type']
)

@pytest.fixture
def alertmanager_url():
    """Get Alertmanager URL."""
    return "http://localhost:9093"

@pytest.fixture
def prometheus_url():
    """Get Prometheus URL."""
    return "http://localhost:9090"

def test_high_error_rate():
    """Test high error rate alert triggering."""
    # Simulate errors
    for _ in range(20):
        ERROR_COUNTER.labels(
            service="test_service",
            error_type="test_error"
        ).inc()
    
    # Wait for alert to fire
    time.sleep(10)
    
    # Verify alert in Prometheus
    response = requests.get(
        "http://localhost:9090/api/v1/alerts",
        params={"query": 'ALERTS{alertname="HighErrorRate"}'}
    )
    assert response.status_code == 200
    alerts = response.json()["data"]["result"]
    assert any(
        alert["metric"]["alertname"] == "HighErrorRate"
        for alert in alerts
    )

def test_high_latency():
    """Test high latency alert triggering."""
    # Simulate slow requests
    for _ in range(10):
        LATENCY_HISTOGRAM.labels(
            service="test_service",
            endpoint="/test"
        ).observe(3.0)  # 3 seconds latency
    
    time.sleep(10)
    
    # Verify alert
    response = requests.get(
        "http://localhost:9090/api/v1/alerts",
        params={"query": 'ALERTS{alertname="HighLatency"}'}
    )
    assert response.status_code == 200
    alerts = response.json()["data"]["result"]
    assert any(
        alert["metric"]["alertname"] == "HighLatency"
        for alert in alerts
    )

def test_service_health():
    """Test service health alert triggering."""
    # Simulate service down
    response = requests.post(
        "http://localhost:9093/api/v1/alerts",
        json=[{
            "labels": {
                "alertname": "ServiceUnhealthy",
                "service": "test_service",
                "severity": "critical"
            },
            "annotations": {
                "description": "Service is down"
            }
        }]
    )
    assert response.status_code == 200
    
    # Verify alert was received
    time.sleep(5)
    response = requests.get("http://localhost:9093/api/v1/alerts")
    assert response.status_code == 200
    alerts = response.json()
    assert any(
        alert["labels"]["alertname"] == "ServiceUnhealthy"
        for alert in alerts
    )

def test_alert_resolution():
    """Test alert resolution flow."""
    # Trigger alert
    ERROR_COUNTER.labels(
        service="test_service",
        error_type="test_error"
    ).inc()
    
    time.sleep(10)
    
    # Verify alert fired
    response = requests.get(
        "http://localhost:9090/api/v1/alerts",
        params={"query": 'ALERTS{alertname="HighErrorRate"}'}
    )
    assert response.status_code == 200
    
    # Wait for resolution
    time.sleep(300)  # 5 minutes
    
    # Verify alert resolved
    response = requests.get(
        "http://localhost:9090/api/v1/alerts",
        params={"query": 'ALERTS{alertname="HighErrorRate"}'}
    )
    assert response.status_code == 200
    alerts = response.json()["data"]["result"]
    assert not any(
        alert["metric"]["alertname"] == "HighErrorRate"
        for alert in alerts
    )

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 