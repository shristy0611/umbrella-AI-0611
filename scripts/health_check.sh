#!/bin/bash

# Health Check Script for UMBRELLA-AI Services
# This script monitors the health of all Docker services

set -e

# Configuration
LOG_FILE="/var/log/umbrella-health.log"
SERVICES=(
    "pdf_extraction:8001"
    "sentiment_analysis:8002"
    "rag_scraper:8003"
    "chatbot:8004"
    "api_gateway:8000"
)

# Create log file if it doesn't exist
sudo touch $LOG_FILE
sudo chown $USER $LOG_FILE

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log "ERROR: Docker is not running"
        return 1
    fi
    return 0
}

check_service() {
    local service=$1
    local port=$2
    
    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
        log "ERROR: Service $service is not running"
        return 1
    fi
    
    # Check if service is healthy
    local health_status=$(docker inspect --format='{{.State.Health.Status}}' "${service}" 2>/dev/null)
    if [ "$health_status" != "healthy" ]; then
        log "WARNING: Service $service health status is: $health_status"
        return 1
    }
    
    # Check if endpoint is responding
    if ! curl -s "http://localhost:${port}/health" >/dev/null; then
        log "ERROR: Service $service health endpoint is not responding"
        return 1
    }
    
    log "INFO: Service $service is healthy"
    return 0
}

check_all_services() {
    local failed=0
    
    # Check Docker first
    if ! check_docker; then
        failed=1
    fi
    
    # Check each service
    for service_info in "${SERVICES[@]}"; do
        IFS=':' read -r service port <<< "$service_info"
        if ! check_service "$service" "$port"; then
            failed=1
        fi
    done
    
    return $failed
}

# Main execution
log "Starting health check..."
if check_all_services; then
    log "All services are healthy"
    exit 0
else
    log "One or more services are unhealthy"
    exit 1
fi 