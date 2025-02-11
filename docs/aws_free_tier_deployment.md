# AWS Free Tier Deployment Guide for UMBRELLA-AI

This guide details the steps to deploy the UMBRELLA-AI Docker environment on an AWS Free Tier EC2 instance.

## Prerequisites

- AWS Free Tier account
- AWS CLI installed and configured locally
- SSH key pair for EC2 instance access

## Step 1: Launch EC2 Instance

1. Launch a t2.micro instance with Amazon Linux 2023:
   ```bash
   aws ec2 run-instances \
     --image-id ami-0c55b159cbfafe1f0 \
     --instance-type t2.micro \
     --key-name your-key-pair \
     --security-group-ids your-security-group \
     --subnet-id your-subnet-id \
     --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=umbrella-ai}]'
   ```

2. Configure security group:
   - Allow SSH (port 22)
   - Allow HTTP (port 80)
   - Allow ports 8000-8004 for services

## Step 2: Connect and Setup

1. Connect to the instance:
   ```bash
   ssh -i /path/to/key.pem ec2-user@your-instance-ip
   ```

2. Run the setup script:
   ```bash
   curl -O https://raw.githubusercontent.com/yourusername/umbrella-ai/main/scripts/aws_setup.sh
   chmod +x aws_setup.sh
   ./aws_setup.sh
   ```

3. Log out and log back in for group changes to take effect:
   ```bash
   exit
   ssh -i /path/to/key.pem ec2-user@your-instance-ip
   ```

## Step 3: Deploy Application

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/umbrella-ai.git
   cd umbrella-ai
   ```

2. Create .env file:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   nano .env
   ```

3. Start the services:
   ```bash
   docker-compose up -d --build
   ```

4. Verify deployment:
   ```bash
   docker ps
   ./scripts/health_check.sh
   ```

## Step 4: Setup Monitoring

1. Make scripts executable:
   ```bash
   chmod +x scripts/health_check.sh
   chmod +x scripts/simulate_failures.sh
   ```

2. Setup cron job for health checks:
   ```bash
   (crontab -l 2>/dev/null; echo "*/5 * * * * /path/to/umbrella-ai/scripts/health_check.sh") | crontab -
   ```

3. Configure logging:
   ```bash
   sudo mkdir -p /var/log/umbrella
   sudo chown -R ec2-user:ec2-user /var/log/umbrella
   ```

## Step 5: Load Testing

1. Install Locust:
   ```bash
   pip3 install locust
   ```

2. Run load tests:
   ```bash
   cd tests/load
   locust -f locustfile.py
   ```

3. Access Locust web interface:
   http://your-instance-ip:8089

## Step 6: Failure Testing

1. Run failure simulation tests:
   ```bash
   ./scripts/simulate_failures.sh
   ```

2. Monitor logs:
   ```bash
   tail -f /var/log/umbrella-health.log
   tail -f /var/log/umbrella-failures.log
   ```

## Maintenance

### Updating Services

```bash
git pull origin main
docker-compose down
docker-compose up -d --build
```

### Backup Logs

```bash
sudo tar czf umbrella-logs-$(date +%Y%m%d).tar.gz /var/log/umbrella/
```

### Cleanup

```bash
docker system prune -af  # Remove unused containers, networks, and images
```

## Troubleshooting

### Common Issues

1. **Services not starting:**
   ```bash
   docker-compose logs
   docker ps -a
   ```

2. **Health check failures:**
   ```bash
   cat /var/log/umbrella-health.log
   docker inspect <container_name>
   ```

3. **Resource constraints:**
   ```bash
   docker stats
   free -m
   df -h
   ```

### Recovery Steps

1. **Restart specific service:**
   ```bash
   docker-compose restart <service_name>
   ```

2. **Full system restart:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

3. **Clear Docker system:**
   ```bash
   docker system prune
   docker volume prune
   ```

## Security Notes

- Keep your AWS credentials secure
- Regularly update security groups
- Monitor instance logs for suspicious activity
- Keep Docker and system packages updated

## Resource Monitoring

Monitor AWS Free Tier usage:
- EC2 hours
- Data transfer
- EBS storage

## Support

For issues or questions:
1. Check logs in `/var/log/umbrella/`
2. Review AWS CloudWatch metrics
3. Open an issue on GitHub
4. Contact support team 