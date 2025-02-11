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

print_blue "Stopping UMBRELLA-AI services..."

# Stop all containers
docker-compose down

if [ $? -eq 0 ]; then
    print_green "All services stopped successfully!"
    
    # Optional cleanup
    read -p "Do you want to clean up unused Docker resources? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_blue "Cleaning up Docker resources..."
        
        # Remove unused containers
        docker container prune -f
        
        # Remove unused images
        docker image prune -f
        
        # Remove unused volumes (only those not attached to containers)
        docker volume prune -f
        
        print_green "Cleanup completed!"
    fi
else
    print_red "Failed to stop services!"
    docker-compose logs
    exit 1
fi 