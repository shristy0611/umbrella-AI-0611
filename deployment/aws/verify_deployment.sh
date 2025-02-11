#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "Verifying UMBRELLA-AI Deployment..."
echo "=================================="

# Function to check service health
check_service() {
    local service_name=$1
    local port=$2
    
    echo -n "Checking $service_name... "
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health)
    
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}Failed (HTTP $response)${NC}"
        return 1
    fi
}

# Check Docker and Docker Compose
echo -n "Checking Docker... "
if docker info >/dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}Failed${NC}"
    exit 1
fi

echo -n "Checking Docker Compose... "
if docker-compose version >/dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}Failed${NC}"
    exit 1
fi

# Check running containers
echo -n "Checking running containers... "
container_count=$(docker ps --format '{{.Names}}' | wc -l)
if [ "$container_count" -gt 0 ]; then
    echo -e "${GREEN}$container_count containers running${NC}"
else
    echo -e "${RED}No containers running${NC}"
    exit 1
fi

# Check each service
echo -e "\nChecking Service Health:"
check_service "Orchestrator" 8000
check_service "PDF Extraction" 8001
check_service "Sentiment Analysis" 8002
check_service "Chatbot" 8003
check_service "RAG Scraper" 8004
check_service "Vector DB" 8005

# Check infrastructure services
echo -e "\nChecking Infrastructure Services:"
echo -n "MongoDB... "
if nc -z localhost 27017; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}Failed${NC}"
fi

echo -n "Redis... "
if nc -z localhost 6379; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}Failed${NC}"
fi

echo -n "RabbitMQ... "
if nc -z localhost 5672; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}Failed${NC}"
fi

# Check monitoring stack
echo -e "\nChecking Monitoring Stack:"
echo -n "Prometheus... "
if nc -z localhost 9090; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}Failed${NC}"
fi

echo -n "Grafana... "
if nc -z localhost 3000; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}Failed${NC}"
fi

echo -n "Jaeger... "
if nc -z localhost 16686; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}Failed${NC}"
fi

# Check disk space
echo -e "\nChecking Disk Space:"
df -h / | awk 'NR==2 {print "Used: "$5" of "$2}'

# Check memory usage
echo -e "\nChecking Memory Usage:"
free -h | awk 'NR==2 {print "Used: "$3" of "$2}'

echo -e "\nDeployment verification complete." 