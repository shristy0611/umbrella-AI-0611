#!/bin/bash

echo "Starting Integration Tests..."
echo "============================"

# Ensure all services are up and healthy
echo "Checking service health..."
docker-compose ps

# Run integration tests through orchestrator service
echo -e "\nRunning integration tests..."
docker-compose exec orchestrator pytest /app/tests/integration/test_service_communication.py -v

# Get the exit code
TEST_EXIT_CODE=$?

echo -e "\nTest Results Summary:"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All integration tests passed!"
else
    echo "❌ Some tests failed. Check the output above for details."
fi

echo -e "\nNetwork Isolation Test..."
./tests/network_isolation_test.sh

exit $TEST_EXIT_CODE 