#!/bin/bash

# AWS EC2 Setup Script for UMBRELLA-AI
# This script installs Docker and Docker Compose on an AWS EC2 instance

set -e

echo "Starting AWS EC2 setup for UMBRELLA-AI..."

# Update system packages
echo "Updating system packages..."
sudo yum update -y

# Install Docker
echo "Installing Docker..."
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# Install Docker Compose
echo "Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install other required tools
echo "Installing additional tools..."
sudo yum install -y git jq curl

# Verify installations
echo "Verifying installations..."
docker --version
docker-compose --version

echo "Setup complete! Please log out and log back in for group changes to take effect." 