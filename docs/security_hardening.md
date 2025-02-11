# UMBRELLA-AI Security Hardening Guide

This guide provides comprehensive security measures for hardening the UMBRELLA-AI deployment on AWS Free Tier.

## Table of Contents
1. [AWS Instance Security](#aws-instance-security)
2. [Docker Security](#docker-security)
3. [Application Security](#application-security)
4. [Network Security](#network-security)
5. [Secrets Management](#secrets-management)
6. [Monitoring and Auditing](#monitoring-and-auditing)

## AWS Instance Security

### EC2 Instance Hardening

1. **Update System Packages**
   ```bash
   sudo yum update -y
   sudo yum install -y yum-cron
   sudo systemctl enable yum-cron
   sudo systemctl start yum-cron
   ```

2. **Configure Automatic Updates**
   ```bash
   # /etc/yum/yum-cron.conf
   update_cmd = security
   apply_updates = yes
   ```

3. **Secure SSH Access**
   ```bash
   # /etc/ssh/sshd_config
   PermitRootLogin no
   PasswordAuthentication no
   MaxAuthTries 3
   Protocol 2
   ```

4. **Set Up Host-based Firewall**
   ```bash
   sudo yum install -y iptables-services
   sudo systemctl enable iptables
   
   # Configure iptables rules
   sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
   sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
   sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
   sudo iptables -A INPUT -p tcp --dport 8000:8004 -j ACCEPT
   sudo iptables -P INPUT DROP
   
   # Save rules
   sudo service iptables save
   ```

### IAM Security

1. **Create Limited IAM Role**
   ```bash
   aws iam create-role \
     --role-name umbrella-ec2-role \
     --assume-role-policy-document file://ec2-trust-policy.json
   ```

2. **Attach Minimal Permissions**
   ```bash
   aws iam put-role-policy \
     --role-name umbrella-ec2-role \
     --policy-name umbrella-permissions \
     --policy-document file://minimal-permissions.json
   ```

Example `minimal-permissions.json`:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            "Resource": "arn:aws:secretsmanager:*:*:secret:umbrella/gemini/*"
        }
    ]
}
```

## Docker Security

### Container Hardening

1. **Run Containers as Non-Root**
   ```dockerfile
   # Dockerfile
   RUN groupadd -r umbrella && useradd -r -g umbrella umbrella
   USER umbrella
   ```

2. **Enable Security Options**
   ```yaml
   # docker-compose.yml
   services:
     api_gateway:
       security_opt:
         - no-new-privileges:true
       cap_drop:
         - ALL
       cap_add:
         - NET_BIND_SERVICE
   ```

3. **Set Resource Limits**
   ```yaml
   services:
     pdf_extraction:
       deploy:
         resources:
           limits:
             cpus: '0.50'
             memory: 512M
           reservations:
             cpus: '0.25'
             memory: 256M
   ```

4. **Enable Docker Content Trust**
   ```bash
   # Enable content trust
   export DOCKER_CONTENT_TRUST=1
   
   # Sign images
   docker trust sign umbrella-pdf-extraction:latest
   ```

### Docker Daemon Security

1. **Configure Daemon Security**
   ```json
   # /etc/docker/daemon.json
   {
     "userns-remap": "default",
     "live-restore": true,
     "userland-proxy": false,
     "no-new-privileges": true,
     "log-driver": "json-file",
     "log-opts": {
       "max-size": "10m",
       "max-file": "3"
     }
   }
   ```

2. **Enable Docker Audit**
   ```bash
   sudo auditctl -w /usr/bin/docker -k docker
   sudo auditctl -w /var/lib/docker -k docker
   sudo auditctl -w /etc/docker -k docker
   sudo auditctl -w /lib/systemd/system/docker.service -k docker
   ```

## Application Security

### API Security

1. **Enable Rate Limiting**
   ```python
   from fastapi import FastAPI, Request
   from fastapi.middleware.throttling import ThrottlingMiddleware

   app = FastAPI()
   app.add_middleware(
       ThrottlingMiddleware,
       rate_limit=100,
       time_window=60
   )
   ```

2. **Configure CORS**
   ```python
   from fastapi.middleware.cors import CORSMiddleware

   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-domain.com"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

3. **Input Validation**
   ```python
   from pydantic import BaseModel, constr

   class SecureInput(BaseModel):
       text: constr(max_length=1000)
       file_type: constr(regex='^[A-Za-z0-9._-]+$')
   ```

### Authentication and Authorization

1. **JWT Configuration**
   ```python
   from jose import JWTError, jwt
   from datetime import datetime, timedelta

   SECRET_KEY = os.getenv("JWT_SECRET_KEY")
   ALGORITHM = "HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES = 30

   def create_access_token(data: dict):
       expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
       expire = datetime.utcnow() + expires_delta
       to_encode = data.copy()
       to_encode.update({"exp": expire})
       return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
   ```

2. **API Key Rotation**
   ```python
   from shared.gemini.config import gemini_config, ServiceType

   async def rotate_api_keys():
       for service_type in ServiceType:
           await gemini_config.rotate_api_key(service_type)
   ```

## Network Security

### Security Groups

1. **Minimal Inbound Rules**
   ```bash
   aws ec2 authorize-security-group-ingress \
     --group-id <security-group-id> \
     --protocol tcp \
     --port 22 \
     --cidr <your-ip>/32
   
   aws ec2 authorize-security-group-ingress \
     --group-id <security-group-id> \
     --protocol tcp \
     --port 80 \
     --cidr 0.0.0.0/0
   ```

2. **Service-Specific Rules**
   ```bash
   # Allow internal service communication
   aws ec2 authorize-security-group-ingress \
     --group-id <security-group-id> \
     --protocol tcp \
     --port 8000-8004 \
     --source-group <security-group-id>
   ```

### TLS Configuration

1. **Generate SSL Certificate**
   ```bash
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout umbrella.key -out umbrella.crt
   ```

2. **Configure Nginx SSL**
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com;
       
       ssl_certificate /etc/nginx/ssl/umbrella.crt;
       ssl_certificate_key /etc/nginx/ssl/umbrella.key;
       
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_ciphers HIGH:!aNULL:!MD5;
       
       location / {
           proxy_pass http://api_gateway:8000;
       }
   }
   ```

## Secrets Management

### AWS Secrets Manager

1. **Create Encrypted Secrets**
   ```bash
   aws secretsmanager create-secret \
     --name umbrella/gemini/api-keys \
     --secret-string file://secrets.json \
     --kms-key-id alias/aws/secretsmanager
   ```

2. **Configure Automatic Rotation**
   ```bash
   aws secretsmanager rotate-secret \
     --secret-id umbrella/gemini/api-keys \
     --rotation-lambda-arn <lambda-arn> \
     --rotation-rules AutomaticallyAfterDays=30
   ```

### Environment Variables

1. **Secure Environment File**
   ```bash
   # Encrypt .env file
   gpg -c .env
   
   # Set restrictive permissions
   chmod 600 .env
   ```

2. **Environment Variable Validation**
   ```python
   from pydantic import BaseSettings, SecretStr

   class Settings(BaseSettings):
       API_KEY: SecretStr
       JWT_SECRET: SecretStr
       
       class Config:
           env_file = '.env'
   ```

## Monitoring and Auditing

### CloudWatch Integration

1. **Enable CloudWatch Logs**
   ```bash
   # Install CloudWatch agent
   sudo yum install -y amazon-cloudwatch-agent
   
   # Configure agent
   sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
   ```

2. **Configure Log Groups**
   ```json
   {
     "logs": {
       "logs_collected": {
         "files": {
           "collect_list": [
             {
               "file_path": "/var/log/umbrella/*.log",
               "log_group_name": "/umbrella/application",
               "log_stream_name": "{instance_id}"
             }
           ]
         }
       }
     }
   }
   ```

### Security Monitoring

1. **Enable AWS GuardDuty**
   ```bash
   aws guardduty create-detector \
     --enable \
     --finding-publishing-frequency FIFTEEN_MINUTES
   ```

2. **Configure CloudWatch Alarms**
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name UmbrellaHighCPU \
     --metric-name CPUUtilization \
     --namespace AWS/EC2 \
     --statistic Average \
     --period 300 \
     --threshold 80 \
     --comparison-operator GreaterThanThreshold \
     --evaluation-periods 2 \
     --alarm-actions <sns-topic-arn>
   ```

### Security Auditing

1. **Enable AWS Config**
   ```bash
   aws configservice start-configuration-recorder \
     --configuration-recorder name=umbrella-config \
     --recording-group allSupported=true
   ```

2. **Configure AWS CloudTrail**
   ```bash
   aws cloudtrail create-trail \
     --name umbrella-audit-trail \
     --s3-bucket-name umbrella-audit-logs \
     --is-multi-region-trail \
     --enable-log-file-validation
   ```

## Best Practices

1. **Regular Security Updates**
   - Update system packages weekly
   - Rotate secrets monthly
   - Review security groups quarterly

2. **Access Control**
   - Use principle of least privilege
   - Implement MFA for AWS access
   - Regular access review

3. **Monitoring**
   - Enable real-time alerts
   - Review audit logs daily
   - Monitor unusual patterns

4. **Incident Response**
   - Maintain incident response plan
   - Regular security drills
   - Document all security events

## Security Checklist

- [ ] System packages updated
- [ ] SSH hardened
- [ ] Firewall configured
- [ ] Docker security options enabled
- [ ] Container resources limited
- [ ] API security implemented
- [ ] Secrets properly managed
- [ ] TLS configured
- [ ] Monitoring enabled
- [ ] Audit logging active
- [ ] Backup encryption enabled
- [ ] Security groups reviewed
- [ ] IAM permissions minimal
- [ ] Auto-updates configured
- [ ] Security alerts tested 