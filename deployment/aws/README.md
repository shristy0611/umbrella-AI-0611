# UMBRELLA-AI AWS Deployment Guide

## Prerequisites
- AWS Account with Free Tier access
- AWS CLI installed and configured
- Terraform installed
- SSH key pair created in AWS

## Deployment Steps

### 1. Initial Setup
```bash
# Clone the repository
git clone https://github.com/shristy0611/umbrella-AI-0611.git
cd umbrella-AI-0611/deployment/aws

# Initialize Terraform
terraform init
```

### 2. Configure AWS Credentials
```bash
# Configure AWS CLI
aws configure
```

### 3. Deploy Infrastructure
```bash
# Create SSH key pair if not exists
aws ec2 create-key-pair --key-name umbrella-ai-key --query 'KeyMaterial' --output text > umbrella-ai-key.pem
chmod 400 umbrella-ai-key.pem

# Deploy using Terraform
terraform apply -var="key_name=umbrella-ai-key"
```

### 4. Connect to EC2 Instance
```bash
# Get the instance IP
export EC2_IP=$(terraform output -raw public_ip)

# SSH into the instance
ssh -i umbrella-ai-key.pem ec2-user@$EC2_IP
```

### 5. Verify Deployment
```bash
# Run verification script
./verify_deployment.sh
```

## Service URLs
After deployment, the following services will be available:

- Orchestrator: http://<EC2_IP>:8000
- PDF Extraction: http://<EC2_IP>:8001
- Sentiment Analysis: http://<EC2_IP>:8002
- Chatbot: http://<EC2_IP>:8003
- RAG Scraper: http://<EC2_IP>:8004
- Vector DB: http://<EC2_IP>:8005

### Monitoring Stack
- Grafana: http://<EC2_IP>:3000
- Prometheus: http://<EC2_IP>:9090
- Jaeger UI: http://<EC2_IP>:16686
- Alertmanager: http://<EC2_IP>:9093

## Environment Variables
The deployment uses the following environment variables from `.env`:
- GEMINI_API_KEY_OCR
- GEMINI_API_KEY_RECOMMENDATION
- GEMINI_API_KEY_SENTIMENT
- GEMINI_API_KEY_CHATBOT
- ORCHESTRATOR_API_KEY
- TASK_DECOMPOSER_API_KEY
- RESULT_VERIFIER_API_KEY

## Monitoring and Maintenance

### Logs
View service logs:
```bash
# View logs for a specific service
docker-compose logs -f <service_name>

# View all logs
docker-compose logs -f
```

### Health Checks
Check service health:
```bash
# Run health check script
./verify_deployment.sh
```

### Backup
Backup data volumes:
```bash
# Create backup directory
mkdir -p /backup

# Backup MongoDB data
docker run --rm --volumes-from mongodb -v /backup:/backup ubuntu tar cvf /backup/mongodb.tar /data/db

# Backup Vector DB data
docker run --rm --volumes-from vector_db -v /backup:/backup ubuntu tar cvf /backup/vector_db.tar /data
```

## Troubleshooting

### Common Issues

1. **Container fails to start**
```bash
# Check container logs
docker-compose logs <service_name>

# Restart container
docker-compose restart <service_name>
```

2. **Memory issues**
```bash
# Check memory usage
free -h

# Clear system cache
sudo sync; echo 3 | sudo tee /proc/sys/vm/drop_caches
```

3. **Disk space issues**
```bash
# Check disk usage
df -h

# Clean up Docker
docker system prune -f
```

### Security Notes
- All API keys are stored in `.env` file
- SSH access is restricted to your IP
- All services use TLS for communication
- Regular security updates are important

## Cleanup
To destroy the infrastructure:
```bash
terraform destroy -var="key_name=umbrella-ai-key"
``` 