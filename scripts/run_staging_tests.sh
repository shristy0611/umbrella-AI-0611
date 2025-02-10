#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test output directory
TEST_OUTPUT_DIR="test-reports/staging"
mkdir -p $TEST_OUTPUT_DIR

echo -e "${YELLOW}Starting UMBRELLA-AI Staging Environment Tests${NC}"
echo "=================================================="

# Function to log messages with timestamp
log_message() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check service health
check_service_health() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:$port/health" | grep -q "healthy"; then
            return 0
        fi
        log_message "Waiting for $service to be healthy (attempt $attempt/$max_attempts)..."
        sleep 2
        attempt=$((attempt + 1))
    done
    return 1
}

# Start staging environment
log_message "Starting staging environment..."
docker-compose -f docker-compose.staging.yml up -d

# Wait for services to be healthy
echo -e "\n${YELLOW}Checking service health...${NC}"
services=(
    "orchestrator:8000"
    "pdf_extraction:8001"
    "sentiment_analysis:8002"
    "chatbot:8003"
    "rag_scraper:8004"
    "vector_db:8005"
)

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if ! check_service_health $name $port; then
        echo -e "${RED}Error: $name service failed to become healthy${NC}"
        exit 1
    fi
    echo -e "${GREEN}$name service is healthy${NC}"
done

# Run tests with coverage
echo -e "\n${YELLOW}Running test suite...${NC}"

# Unit tests
echo -e "\n${YELLOW}Running unit tests...${NC}"
pytest tests/unit \
    --junitxml=$TEST_OUTPUT_DIR/unit-tests.xml \
    --html=$TEST_OUTPUT_DIR/unit-tests.html \
    -v || test_exit_code=$?

# Integration tests
echo -e "\n${YELLOW}Running integration tests...${NC}"
pytest tests/integration \
    --junitxml=$TEST_OUTPUT_DIR/integration-tests.xml \
    --html=$TEST_OUTPUT_DIR/integration-tests.html \
    -v || test_exit_code=$?

# E2E tests
echo -e "\n${YELLOW}Running end-to-end tests...${NC}"
pytest tests/e2e \
    --junitxml=$TEST_OUTPUT_DIR/e2e-tests.xml \
    --html=$TEST_OUTPUT_DIR/e2e-tests.html \
    -v || test_exit_code=$?

# Generate coverage report
echo -e "\n${YELLOW}Generating coverage report...${NC}"
coverage run -m pytest tests/
coverage html -d $TEST_OUTPUT_DIR/coverage
coverage xml -o $TEST_OUTPUT_DIR/coverage.xml
coverage report > $TEST_OUTPUT_DIR/coverage.txt

# Collect logs
echo -e "\n${YELLOW}Collecting service logs...${NC}"
mkdir -p $TEST_OUTPUT_DIR/logs
for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    docker-compose -f docker-compose.staging.yml logs $name > "$TEST_OUTPUT_DIR/logs/$name.log"
done

# Collect metrics
echo -e "\n${YELLOW}Collecting metrics...${NC}"
curl -s localhost:9090/api/v1/query?query=umbrella_requests_total > $TEST_OUTPUT_DIR/metrics_requests.json
curl -s localhost:9090/api/v1/query?query=umbrella_errors_total > $TEST_OUTPUT_DIR/metrics_errors.json
curl -s localhost:9090/api/v1/query?query=umbrella_request_duration_seconds > $TEST_OUTPUT_DIR/metrics_latency.json

# Generate summary report
echo -e "\n${YELLOW}Generating test summary...${NC}"
cat << EOF > $TEST_OUTPUT_DIR/summary.md
# UMBRELLA-AI Staging Test Summary
Generated: $(date)

## Test Results
- Unit Tests: $(grep "errors=" $TEST_OUTPUT_DIR/unit-tests.xml | sed 's/.*errors="\([^"]*\)".*/\1/' || echo "N/A") errors
- Integration Tests: $(grep "errors=" $TEST_OUTPUT_DIR/integration-tests.xml | sed 's/.*errors="\([^"]*\)".*/\1/' || echo "N/A") errors
- E2E Tests: $(grep "errors=" $TEST_OUTPUT_DIR/e2e-tests.xml | sed 's/.*errors="\([^"]*\)".*/\1/' || echo "N/A") errors

## Coverage Summary
$(tail -n 5 $TEST_OUTPUT_DIR/coverage.txt)

## Service Health
$(for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    curl -s "http://localhost:$port/health" | jq -r '. | "- \(.service): \(.status)"'
done)

## Metrics Summary
- Total Requests: $(curl -s localhost:9090/api/v1/query?query=sum\(umbrella_requests_total\) | jq '.data.result[0].value[1]')
- Total Errors: $(curl -s localhost:9090/api/v1/query?query=sum\(umbrella_errors_total\) | jq '.data.result[0].value[1]')
- Average Latency: $(curl -s localhost:9090/api/v1/query?query=avg\(rate\(umbrella_request_duration_seconds_sum\[5m\]\)\/rate\(umbrella_request_duration_seconds_count\[5m\]\)\) | jq '.data.result[0].value[1]')s
EOF

# Check if any tests failed
if [ "$test_exit_code" != "0" ]; then
    echo -e "${RED}Some tests failed. Check the reports in $TEST_OUTPUT_DIR${NC}"
    exit $test_exit_code
fi

echo -e "${GREEN}All tests completed successfully!${NC}"
echo "Test reports and logs are available in $TEST_OUTPUT_DIR"

# Cleanup
read -p "Do you want to stop the staging environment? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${YELLOW}Stopping staging environment...${NC}"
    docker-compose -f docker-compose.staging.yml down
fi 