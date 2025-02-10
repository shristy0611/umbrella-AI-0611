#!/bin/bash

# Start services in the background
echo "Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Run tests
echo "Running tests..."
python -m pytest

# Get test result
TEST_RESULT=$?

# Stop services
echo "Stopping services..."
docker-compose down

# Exit with test result
exit $TEST_RESULT 