#!/bin/bash

# Update system packages
sudo yum update -y

# Install Docker
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user
sudo chkconfig docker on

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
sudo yum install -y git

# Create app directory
mkdir -p /home/ec2-user/umbrella-ai
cd /home/ec2-user/umbrella-ai

# Clone the repository (you'll need to add your repository URL)
git clone https://github.com/shristy0611/umbrella-AI-0611.git .

# Set up environment variables
cp .env.example .env

# Create necessary directories
mkdir -p data/vector_db
mkdir -p logs
mkdir -p test-reports/coverage

# Set permissions
sudo chown -R ec2-user:ec2-user /home/ec2-user/umbrella-ai

# Start the services
docker-compose up -d

# Print container status
docker ps 