#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Running UMBRELLA-AI Test Suite${NC}"
echo "=================================="

# Create coverage directory if it doesn't exist
mkdir -p tests/coverage

# Function to run tests with proper formatting
run_test_suite() {
    local suite_name=$1
    local test_path=$2
    
    echo -e "\n${BLUE}Running $suite_name Tests${NC}"
    echo "------------------------"
    
    pytest $test_path -v \
          --cov=src \
          --cov-report=term-missing \
          --cov-report=html:tests/coverage/$suite_name \
          --cov-fail-under=80
    
    local result=$?
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✓ $suite_name Tests Passed${NC}"
    else
        echo -e "${RED}✗ $suite_name Tests Failed${NC}"
        exit $result
    fi
}

# Run each test suite
run_test_suite "Unit" "tests/unit"
run_test_suite "Integration" "tests/integration"
run_test_suite "E2E" "tests/e2e"

# Generate combined coverage report
coverage combine
coverage html -d tests/coverage/combined

echo -e "\n${BLUE}Test Summary${NC}"
echo "=============="
coverage report

# Check if all tests passed
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed successfully!${NC}"
    echo "Coverage reports generated in tests/coverage/"
    exit 0
else
    echo -e "\n${RED}Some tests failed. Please check the output above.${NC}"
    exit 1
fi 