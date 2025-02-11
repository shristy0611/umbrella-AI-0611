#!/bin/bash

# Failure Simulation Script for UMBRELLA-AI
# This script simulates various failure scenarios and tests system recovery

set -e

# Configuration
LOG_FILE="/var/log/umbrella-failures.log"
SERVICES=(
    "pdf_extraction"
    "sentiment_analysis"
    "rag_scraper"
    "chatbot"
    "api_gateway"
)

# Create log file if it doesn't exist
sudo touch $LOG_FILE
sudo chown $USER $LOG_FILE

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

simulate_container_failure() {
    local service=$1
    log "Simulating failure for service: $service"
    
    # Stop the container
    log "Stopping container $service..."
    docker stop $service
    
    # Wait for health check to detect failure
    sleep 10
    
    # Check if health check detected the failure
    if bash scripts/health_check.sh | grep -q "ERROR: Service $service is not running"; then
        log "Health check successfully detected service failure"
    else
        log "WARNING: Health check did not detect service failure"
    fi
    
    # Restart the container
    log "Restarting container $service..."
    docker start $service
    
    # Wait for service to recover
    sleep 20
    
    # Verify recovery
    if bash scripts/health_check.sh | grep -q "INFO: Service $service is healthy"; then
        log "Service $service successfully recovered"
        return 0
    else
        log "ERROR: Service $service failed to recover"
        return 1
    fi
}

simulate_network_failure() {
    local service=$1
    log "Simulating network failure for service: $service"
    
    # Add network delay
    docker exec $service tc qdisc add dev eth0 root netem delay 1000ms
    
    # Wait for health check to detect degraded performance
    sleep 10
    
    # Remove network delay
    docker exec $service tc qdisc del dev eth0 root
    
    # Wait for service to recover
    sleep 10
    
    # Verify recovery
    if bash scripts/health_check.sh | grep -q "INFO: Service $service is healthy"; then
        log "Service $service recovered from network failure"
        return 0
    else
        log "ERROR: Service $service failed to recover from network failure"
        return 1
    fi
}

simulate_resource_exhaustion() {
    local service=$1
    log "Simulating resource exhaustion for service: $service"
    
    # Start stress test
    docker exec $service stress --cpu 4 --io 2 --vm 2 --vm-bytes 128M --timeout 30s
    
    # Wait for stress test to complete
    sleep 35
    
    # Verify recovery
    if bash scripts/health_check.sh | grep -q "INFO: Service $service is healthy"; then
        log "Service $service recovered from resource exhaustion"
        return 0
    else
        log "ERROR: Service $service failed to recover from resource exhaustion"
        return 1
    fi
}

run_all_tests() {
    local failed=0
    
    for service in "${SERVICES[@]}"; do
        log "Starting failure simulation tests for $service"
        
        # Container failure test
        if ! simulate_container_failure $service; then
            failed=1
        fi
        
        # Network failure test
        if ! simulate_network_failure $service; then
            failed=1
        fi
        
        # Resource exhaustion test
        if ! simulate_resource_exhaustion $service; then
            failed=1
        fi
        
        log "Completed failure simulation tests for $service"
    done
    
    return $failed
}

# Main execution
log "Starting failure simulation tests..."
if run_all_tests; then
    log "All failure simulation tests completed successfully"
    exit 0
else
    log "One or more failure simulation tests failed"
    exit 1
fi 