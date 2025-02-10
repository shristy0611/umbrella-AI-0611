#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting Interface Tests${NC}"
echo "============================"

# Create test data directory if it doesn't exist
mkdir -p tests/data

# Set environment variables for service URLs
export PDF_SERVICE_URL="http://localhost:8001"
export SENTIMENT_SERVICE_URL="http://localhost:8002"
export CHATBOT_SERVICE_URL="http://localhost:8003"
export SCRAPER_SERVICE_URL="http://localhost:8004"
export VECTOR_DB_URL="http://localhost:8005"

# Run the tests
echo -e "\n${GREEN}Running interface tests...${NC}"
pytest tests/integration/test_interfaces.py -v

# Get the exit code
TEST_EXIT_CODE=$?

echo -e "\n${GREEN}Test Results Summary:${NC}"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All interface tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed. Check the output above for details.${NC}"
fi

exit $TEST_EXIT_CODE 