# UMBRELLA-AI Troubleshooting Guide

This guide provides detailed steps for diagnosing and resolving common issues that may occur during deployment and operation of the UMBRELLA-AI system.

## Table of Contents
1. [Container Startup Issues](#container-startup-issues)
2. [Network Connectivity Problems](#network-connectivity-problems)
3. [API Key and Authentication Issues](#api-key-and-authentication-issues)
4. [Resource Constraints](#resource-constraints)
5. [Logging and Monitoring Issues](#logging-and-monitoring-issues)
6. [AWS Free Tier Specific Issues](#aws-free-tier-specific-issues)

## Container Startup Issues

### Container Fails to Start

**Symptoms:**
- Container status shows "Exited" or "Created"
- Health check fails for specific service
- Docker logs show startup errors

**Diagnostic Steps:**
1. Check container status:
   ```bash
   docker ps -a | grep umbrella
   ```

2. View container logs:
   ```bash
   docker logs <container_name>
   docker-compose logs <service_name>
   ```

3. Verify environment variables:
   ```bash
   docker exec <container_name> env
   ```

**Common Solutions:**
1. Environment variable issues:
   ```bash
   # Check .env file exists and has correct permissions
   ls -l .env
   # Verify .env format
   cat .env | grep -v '^#' | grep .
   ```

2. Port conflicts:
   ```bash
   # Check for port usage
   sudo lsof -i :<port_number>
   # Update port mapping in docker-compose.yml if needed
   ```

3. Volume mount issues:
   ```bash
   # Verify volume paths
   docker volume ls
   docker volume inspect <volume_name>
   ```

### Container Restarts Continuously

**Symptoms:**
- Container status cycles between "Up" and "Restarting"
- Health checks fail intermittently

**Diagnostic Steps:**
1. Check restart count:
   ```bash
   docker inspect <container_name> | grep RestartCount
   ```

2. Monitor container health:
   ```bash
   docker events --filter container=<container_name>
   ```

**Solutions:**
1. Adjust health check parameters:
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:<port>/health"]
     interval: 30s
     timeout: 10s
     retries: 3
   ```

2. Increase resource limits:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '0.50'
         memory: 512M
   ```

## Network Connectivity Problems

### Service Discovery Issues

**Symptoms:**
- Services cannot communicate with each other
- DNS resolution fails
- Connection timeouts

**Diagnostic Steps:**
1. Check Docker network:
   ```bash
   docker network ls
   docker network inspect umbrella_default
   ```

2. Test inter-service connectivity:
   ```bash
   docker exec <container_name> ping <service_name>
   docker exec <container_name> curl http://<service_name>:<port>/health
   ```

**Solutions:**
1. Recreate Docker network:
   ```bash
   docker-compose down
   docker network prune
   docker-compose up -d
   ```

2. Update DNS settings:
   ```bash
   # Add custom DNS to docker-compose.yml
   dns:
     - 8.8.8.8
     - 8.8.4.4
   ```

### External API Access Issues

**Symptoms:**
- Cannot access external APIs (e.g., Gemini API)
- SSL/TLS errors
- Timeout errors

**Diagnostic Steps:**
1. Check external connectivity:
   ```bash
   docker exec <container_name> curl -v https://api.external-service.com
   ```

2. Verify SSL certificates:
   ```bash
   docker exec <container_name> openssl s_client -connect api.external-service.com:443
   ```

**Solutions:**
1. Update CA certificates:
   ```bash
   docker exec <container_name> update-ca-certificates
   ```

2. Configure proxy settings if needed:
   ```bash
   export HTTP_PROXY="http://proxy:port"
   export HTTPS_PROXY="http://proxy:port"
   ```

## API Key and Authentication Issues

### Gemini API Authentication Failures

**Symptoms:**
- API calls return 401/403 errors
- Key rotation fails
- Authentication timeouts

**Diagnostic Steps:**
1. Check API key configuration:
   ```bash
   # Verify AWS Secrets Manager configuration
   aws secretsmanager list-secrets
   aws secretsmanager get-secret-value --secret-id umbrella/gemini/api-keys
   ```

2. Test API key validity:
   ```python
   python3 -c "
   import google.generativeai as genai
   genai.configure(api_key='your-key')
   model = genai.GenerativeModel('gemini-pro')
   response = model.generate_content('test')
   print(response)
   "
   ```

**Solutions:**
1. Rotate API keys:
   ```bash
   python3 scripts/migrate_to_secrets_manager.py --rotate
   ```

2. Update environment variables:
   ```bash
   source .env
   docker-compose up -d --force-recreate
   ```

## Resource Constraints

### Memory Issues

**Symptoms:**
- Container OOM (Out of Memory) kills
- Performance degradation
- Swap usage increases

**Diagnostic Steps:**
1. Monitor memory usage:
   ```bash
   docker stats
   free -m
   ```

2. Check container limits:
   ```bash
   docker inspect <container_name> | grep -A 10 "Memory"
   ```

**Solutions:**
1. Adjust memory limits:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 1G
       reservations:
         memory: 512M
   ```

2. Enable swap (if necessary):
   ```bash
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

### CPU Constraints

**Symptoms:**
- High CPU usage
- Slow response times
- Process throttling

**Diagnostic Steps:**
1. Monitor CPU usage:
   ```bash
   top
   docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
   ```

2. Check system load:
   ```bash
   uptime
   cat /proc/loadavg
   ```

**Solutions:**
1. Adjust CPU limits:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '0.75'
   ```

2. Enable CPU scheduling:
   ```yaml
   cpu_shares: 512
   cpu_quota: 50000
   ```

## Logging and Monitoring Issues

### Log Collection Problems

**Symptoms:**
- Missing logs
- Log rotation failures
- Disk space warnings

**Diagnostic Steps:**
1. Check log files:
   ```bash
   ls -lh /var/log/umbrella/
   df -h /var/log
   ```

2. Verify log configuration:
   ```bash
   docker inspect --format='{{.HostConfig.LogConfig}}' <container_name>
   ```

**Solutions:**
1. Configure log rotation:
   ```bash
   sudo logrotate -f /etc/logrotate.d/docker-container
   ```

2. Update logging driver:
   ```yaml
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

### Metrics Collection Issues

**Symptoms:**
- Missing metrics
- Prometheus scrape failures
- Incomplete monitoring data

**Diagnostic Steps:**
1. Check metrics endpoint:
   ```bash
   curl http://localhost:9090/metrics
   ```

2. Verify Prometheus configuration:
   ```bash
   docker exec prometheus promtool check config /etc/prometheus/prometheus.yml
   ```

**Solutions:**
1. Restart metrics collection:
   ```bash
   systemctl restart prometheus
   python3 scripts/collect_metrics.py
   ```

2. Update scrape configuration:
   ```yaml
   scrape_configs:
     - job_name: 'umbrella'
       static_configs:
         - targets: ['localhost:9090']
   ```

## AWS Free Tier Specific Issues

### Resource Usage Limits

**Symptoms:**
- AWS billing alerts
- Service throttling
- Instance performance degradation

**Diagnostic Steps:**
1. Check AWS usage:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/EC2 \
     --metric-name CPUUtilization \
     --dimensions Name=InstanceId,Value=<instance-id> \
     --start-time $(date -u +%Y-%m-%dT%H:%M:%S -d '7 days ago') \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 3600 \
     --statistics Maximum
   ```

2. Monitor Free Tier limits:
   ```bash
   aws ce get-cost-and-usage \
     --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
     --granularity MONTHLY \
     --metrics UsageQuantity
   ```

**Solutions:**
1. Optimize resource usage:
   ```bash
   # Enable container resource limits
   docker-compose up -d --scale pdf_extraction=1 --scale sentiment_analysis=1
   ```

2. Set up AWS budget alerts:
   ```bash
   aws budgets create-budget \
     --account-id <account-id> \
     --budget file://budget.json \
     --notifications-with-subscribers file://notifications.json
   ```

### Instance Connectivity

**Symptoms:**
- SSH connection failures
- Service unavailability
- Network timeouts

**Diagnostic Steps:**
1. Check instance status:
   ```bash
   aws ec2 describe-instance-status --instance-ids <instance-id>
   ```

2. Verify security group rules:
   ```bash
   aws ec2 describe-security-groups \
     --group-ids <security-group-id>
   ```

**Solutions:**
1. Update security group rules:
   ```bash
   aws ec2 authorize-security-group-ingress \
     --group-id <security-group-id> \
     --protocol tcp \
     --port 22 \
     --cidr <your-ip>/32
   ```

2. Check instance network configuration:
   ```bash
   aws ec2 describe-network-interfaces \
     --filters Name=attachment.instance-id,Values=<instance-id>
   ```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [AWS Free Tier Documentation](https://aws.amazon.com/free/)
- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)
- [Google Gemini API Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)

## Support

If you encounter issues not covered in this guide:
1. Check the latest logs: `tail -f /var/log/umbrella/*.log`
2. Review the deployment summary report
3. Open an issue on GitHub with detailed error information
4. Contact the support team with the generated error reports 