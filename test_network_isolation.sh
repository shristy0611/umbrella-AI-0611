#!/bin/bash

echo "Starting Network Isolation Tests..."
echo "=================================="

# Test 1: Verify orchestrator can reach internal services
echo "Test 1: Orchestrator connectivity to internal services"
docker exec umbrellaai-orchestrator-1 curl -s -o /dev/null -w "%{http_code}" http://pdf_extraction:8001/health && echo " - PDF Service reachable from orchestrator" || echo " - PDF Service not reachable from orchestrator"
docker exec umbrellaai-orchestrator-1 curl -s -o /dev/null -w "%{http_code}" http://sentiment:8002/health && echo " - Sentiment Service reachable from orchestrator" || echo " - Sentiment Service not reachable from orchestrator"
docker exec umbrellaai-orchestrator-1 curl -s -o /dev/null -w "%{http_code}" http://chatbot:8003/health && echo " - Chatbot Service reachable from orchestrator" || echo " - Chatbot Service not reachable from orchestrator"
docker exec umbrellaai-orchestrator-1 curl -s -o /dev/null -w "%{http_code}" http://vector_db:8004/health && echo " - Vector DB reachable from orchestrator" || echo " - Vector DB not reachable from orchestrator"

echo -e "
Test 2: Internal services external network access"
# Test 2: Verify internal services cannot access external network
docker exec umbrellaai-pdf_extraction-1 curl -s -o /dev/null -w "%{http_code}" http://example.com && echo " - PDF Service can access external network (FAIL)" || echo " - PDF Service cannot access external network (PASS)"
docker exec umbrellaai-sentiment-1 curl -s -o /dev/null -w "%{http_code}" http://example.com && echo " - Sentiment Service can access external network (FAIL)" || echo " - Sentiment Service cannot access external network (PASS)"

echo -e "
Test 3: Service dependency connectivity"
# Test 3: Verify service dependencies
docker exec umbrellaai-chatbot-1 curl -s -o /dev/null -w "%{http_code}" http://vector_db:8004/health && echo " - Chatbot can reach Vector DB" || echo " - Chatbot cannot reach Vector DB"
docker exec umbrellaai-chatbot-1 redis-cli -h redis ping > /dev/null && echo " - Chatbot can reach Redis" || echo " - Chatbot cannot reach Redis"

echo -e "
Test 4: External access restrictions"
# Test 4: Verify external access restrictions
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health && echo " - Orchestrator API externally accessible" || echo " - Orchestrator API not externally accessible"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health && echo " - PDF Service externally accessible (FAIL)" || echo " - PDF Service not externally accessible (PASS)"
curl -s -o /dev/null -w "%{http_code}" http://localhost:15672 && echo " - RabbitMQ management interface externally accessible" || echo " - RabbitMQ management interface not externally accessible"

echo -e "
Network Isolation Tests Complete"
echo "=================================="
