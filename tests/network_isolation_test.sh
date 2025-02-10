#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "Starting network isolation tests..."

# Test 1: Verify orchestrator can reach all services
echo -e "\n${GREEN}Test 1: Orchestrator connectivity to internal services${NC}"
docker-compose exec orchestrator curl -s -o /dev/null -w "%{http_code}" http://pdf_extraction:8001/health
echo -e "\nOrchestrator -> PDF Service: $?"
docker-compose exec orchestrator curl -s -o /dev/null -w "%{http_code}" http://sentiment:8002/health
echo -e "Orchestrator -> Sentiment Service: $?"
docker-compose exec orchestrator curl -s -o /dev/null -w "%{http_code}" http://chatbot:8003/health
echo -e "Orchestrator -> Chatbot Service: $?"
docker-compose exec orchestrator curl -s -o /dev/null -w "%{http_code}" http://vector_db:8005/health
echo -e "Orchestrator -> Vector DB: $?"

# Test 2: Verify internal services cannot reach external network
echo -e "\n${GREEN}Test 2: Internal services external network access${NC}"
docker-compose exec pdf_extraction curl -s -o /dev/null -w "%{http_code}" http://example.com
echo -e "PDF Service -> External: $? (Should fail)"
docker-compose exec sentiment curl -s -o /dev/null -w "%{http_code}" http://example.com
echo -e "Sentiment Service -> External: $? (Should fail)"

# Test 3: Verify services can reach their dependencies
echo -e "\n${GREEN}Test 3: Service dependency connectivity${NC}"
docker-compose exec chatbot curl -s -o /dev/null -w "%{http_code}" http://vector_db:8005/health
echo -e "Chatbot -> Vector DB: $?"
docker-compose exec chatbot curl -s -o /dev/null -w "%{http_code}" http://redis:6379
echo -e "Chatbot -> Redis: $?"

# Test 4: Verify external access is restricted
echo -e "\n${GREEN}Test 4: External access restrictions${NC}"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
echo -e "External -> Orchestrator API: $?"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health
echo -e "External -> PDF Service: $? (Should fail)"
curl -s -o /dev/null -w "%{http_code}" http://localhost:15672
echo -e "External -> RabbitMQ Management: $?"

echo -e "\nNetwork isolation test complete!" 