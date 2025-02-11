#!/bin/bash

# Set color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print with color
print_green() { echo -e "${GREEN}$1${NC}"; }
print_red() { echo -e "${RED}$1${NC}"; }
print_blue() { echo -e "${BLUE}$1${NC}"; }

# Check if .env file exists
if [ ! -f .env ]; then
    print_red "Error: .env file not found!"
    print_blue "Creating .env from .env.example..."
    cp .env.example .env
    print_green "Created .env file. Please update it with your API keys and configurations."
    exit 1
fi

# Build and start services
print_blue "Building and starting UMBRELLA-AI services..."

# Build base image first
print_blue "Building base image..."
docker-compose build base

if [ $? -eq 0 ]; then
    print_green "Base image built successfully!"
else
    print_red "Failed to build base image!"
    exit 1
fi

# Build and start all services
print_blue "Building and starting all services..."
docker-compose up -d --build

if [ $? -eq 0 ]; then
    print_green "All services started successfully!"
    
    # Wait for services to be healthy
    print_blue "Waiting for services to be healthy..."
    sleep 10
    
    # Check service health
    services=("orchestrator:8000" "pdf_extraction:8001" "sentiment_analysis:8002" "chatbot:8003" "rag_scraper:8004" "vector_db:8005")
    
    for service in "${services[@]}"; do
        IFS=':' read -r -a array <<< "$service"
        name="${array[0]}"
        port="${array[1]}"
        
        print_blue "Checking $name service..."
        curl -s "http://localhost:$port/health" > /dev/null
        
        if [ $? -eq 0 ]; then
            print_green "$name service is healthy!"
        else
            print_red "$name service is not responding!"
        fi
    done
    
    print_green "\nUMBRELLA-AI is ready!"
    print_blue "Access the services at:"
    print_blue "- Orchestrator API: http://localhost:8000"
    print_blue "- PDF Extraction: http://localhost:8001"
    print_blue "- Sentiment Analysis: http://localhost:8002"
    print_blue "- Chatbot: http://localhost:8003"
    print_blue "- RAG Scraper: http://localhost:8004"
    print_blue "- Vector DB: http://localhost:8005"
    print_blue "- RabbitMQ Management: http://localhost:15672"
    
else
    print_red "Failed to start services!"
    docker-compose logs
    exit 1
fi 