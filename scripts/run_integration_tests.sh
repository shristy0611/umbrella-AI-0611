#!/bin/bash

# Set environment variables for Docker service URLs
export ORCHESTRATOR_URL="http://orchestrator:8000"
export PDF_SERVICE_URL="http://pdf_extraction:8001"
export SENTIMENT_SERVICE_URL="http://sentiment:8002"
export CHATBOT_SERVICE_URL="http://chatbot:8003"
export SCRAPER_SERVICE_URL="http://rag_scraper:8004"
export VECTOR_DB_URL="http://vector_db:8005"

# Run tests inside the orchestrator container
docker compose exec orchestrator python -m pytest /app/tests/integration/test_service_communication.py -v 