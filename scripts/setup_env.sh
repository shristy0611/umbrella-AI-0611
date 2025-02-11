#!/bin/bash

# Gemini API Keys for different services
export GEMINI_API_KEY_OCR="AIzaSyCM9ySEXd0Yc6hdZQQg8HPkuUpYpFwqrsk"
export GEMINI_API_KEY_RECOMMENDATION="AIzaSyAuZ0sEHlF3Wzm5fd0LjjIh-wzlG068xlU"
export GEMINI_API_KEY_SENTIMENT="AIzaSyB3O6Qlk8PIFIy-uwhSv13V2pH1izgDerI"
export GEMINI_API_KEY_CHATBOT="AIzaSyDEu3Eydwkr3_78yaVbg9NGrsj3Ce36pvg"

# Gemini API Keys for orchestration
export ORCHESTRATOR_API_KEY="AIzaSyDFJlkmasG8oAKb-5WYJ8yywDzUO1CCZ-I"
export TASK_DECOMPOSER_API_KEY="AIzaSyDfF0UmcAUlHGV7C3JlEUBX7Y35Ch6HmSU"
export RESULT_VERIFIER_API_KEY="AIzaSyDnGckjrpYClrletBQWovZiIO3boo4oFFk"

# Set default GEMINI_API_KEY for general usage
export GEMINI_API_KEY="AIzaSyCM9ySEXd0Yc6hdZQQg8HPkuUpYpFwqrsk"

# Service URLs
export PDF_SERVICE_URL="http://localhost:8001"
export SENTIMENT_SERVICE_URL="http://localhost:8002"
export CHATBOT_SERVICE_URL="http://localhost:8003"
export SCRAPER_SERVICE_URL="http://localhost:8004"
export VECTOR_DB_URL="http://localhost:8005"

# Database Configuration
export MONGODB_URI="mongodb://mongodb:27017/umbrella"
export VECTOR_DB_PATH="./data/vector_db"

# Message Queue Configuration
export REDIS_URL="redis://redis:6379/0"
export RABBITMQ_URL="amqp://guest:guest@rabbitmq:5672/"

# Logging and Environment
export LOG_LEVEL="INFO"
export ENVIRONMENT="development"

echo "Environment variables set successfully" 