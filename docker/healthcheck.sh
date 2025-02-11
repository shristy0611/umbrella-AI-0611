#!/bin/bash

# Get service port from environment or use default
PORT="${PORT:-8000}"

# Try to get health status
response=$(curl -s -w "%{http_code}" "http://localhost:${PORT}/health" -o /dev/null)

if [ "$response" = "200" ]; then
    exit 0
else
    echo "Health check failed with status: $response"
    exit 1
fi 