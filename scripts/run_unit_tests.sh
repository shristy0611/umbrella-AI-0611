#!/bin/bash

# Set up environment
echo "Setting up test environment..."
source test_env/bin/activate

# Install package in development mode
echo "Installing package in development mode..."
pip install -e .

# Run pytest with coverage
echo "Running unit tests with coverage..."
PYTHONPATH=$PYTHONPATH:$(pwd) pytest tests/unit/ \
    --cov=pdf_extraction_service \
    --cov=sentiment_service \
    --cov=rag_scraper_service \
    --cov=chatbot_service \
    --cov-report=term-missing \
    --cov-report=html:tests/coverage \
    -v

# Check test status
if [ $? -eq 0 ]; then
    echo "All tests passed successfully!"
    echo "Coverage report generated in tests/coverage/"
else
    echo "Some tests failed. Please check the output above."
    exit 1
fi

# Deactivate virtual environment
deactivate 