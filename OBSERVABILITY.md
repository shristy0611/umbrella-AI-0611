# UMBRELLA-AI Observability Guide

## Overview
This guide explains how to use the observability features in UMBRELLA-AI, including logging, tracing, and metrics collection.

## Setting Up

1. Start the observability stack:
```bash
docker-compose -f docker-compose.observability.yml up -d
```

2. Add middleware to your FastAPI service:
```python
from shared.middleware import setup_middleware

app = FastAPI()
setup_middleware(app, "your_service_name")
```

3. Use logging in your code:
```python
from shared.logging_config import log_with_context
import logging

logger = logging.getLogger(__name__)

@app.get("/example")
async def example_endpoint(request: Request):
    log_with_context(
        logger,
        logging.INFO,
        "Processing request",
        correlation_id=request.headers.get("X-Correlation-ID"),
        extra={"custom_data": "example"}
    )
    # Your code here
```

## Accessing Observability Features

### Logs
- Structured JSON logs are written to stdout and can be viewed using:
```bash
docker logs <service_name>
```

### Metrics
1. View service metrics:
```bash
curl http://localhost:8000/metrics
```

2. Access Prometheus UI:
- Open http://localhost:9090 in your browser
- Use the Query interface to explore metrics
- Common metrics:
  - `umbrella_requests_total`: Total requests by service/endpoint
  - `umbrella_request_duration_seconds`: Request duration histogram
  - `umbrella_errors_total`: Error count by type

### Distributed Tracing
1. Access Jaeger UI:
- Open http://localhost:16686 in your browser
- Select a service from the dropdown
- View traces, including:
  - Request flow across services
  - Timing information
  - Error details
  - Correlation IDs

2. Trace Context Propagation:
- Traces are automatically propagated between services
- Use the `X-Correlation-ID` header for request tracking
- Trace IDs are included in logs for correlation

## Best Practices

1. Logging:
- Use structured logging with context
- Include correlation IDs
- Add relevant custom fields using `extra`

2. Metrics:
- Monitor error rates and latencies
- Set up alerts for anomalies
- Use labels effectively

3. Tracing:
- Add custom spans for important operations
- Include relevant attributes
- Use sampling appropriately

## Troubleshooting

1. Missing Traces:
- Verify OpenTelemetry collector is running
- Check service connectivity to collector
- Validate trace context propagation

2. Missing Metrics:
- Confirm Prometheus target configuration
- Check service `/metrics` endpoint
- Verify service registration

3. Logging Issues:
- Check log levels
- Verify JSON formatting
- Ensure correlation ID propagation 