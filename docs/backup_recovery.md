# UMBRELLA-AI Backup and Recovery Procedures

This document outlines the procedures for backing up and recovering the UMBRELLA-AI system components, including data, configurations, and container states.

## Table of Contents
1. [Backup Procedures](#backup-procedures)
2. [Recovery Procedures](#recovery-procedures)
3. [Automated Backup Scripts](#automated-backup-scripts)
4. [Disaster Recovery Plan](#disaster-recovery-plan)

## Backup Procedures

### 1. Configuration Backup

#### Environment Variables and API Keys
```bash
# Backup .env file
cp .env .env.backup.$(date +%Y%m%d)

# Export AWS Secrets
aws secretsmanager get-secret-value \
  --secret-id umbrella/gemini/api-keys \
  --query 'SecretString' \
  --output text > secrets_backup_$(date +%Y%m%d).json
```

#### Docker Compose Configuration
```bash
# Backup Docker Compose files
tar czf docker-compose-backup-$(date +%Y%m%d).tar.gz \
  docker-compose.yml \
  docker-compose.*.yml
```

### 2. Data Backup

#### Vector Database
```bash
# Stop the vector database service
docker-compose stop vector_db

# Backup vector database files
tar czf vector-db-backup-$(date +%Y%m%d).tar.gz \
  ./data/vector_db/

# Restart the service
docker-compose start vector_db
```

#### MongoDB Data
```bash
# Create MongoDB backup
docker exec mongodb mongodump \
  --out /backup/mongodb-$(date +%Y%m%d)

# Copy backup files from container
docker cp \
  mongodb:/backup/mongodb-$(date +%Y%m%d) \
  ./backups/mongodb/
```

### 3. Log Files
```bash
# Compress and archive logs
sudo tar czf \
  umbrella-logs-$(date +%Y%m%d).tar.gz \
  /var/log/umbrella/
```

### 4. Container Images
```bash
# Save container images
docker save -o umbrella-images-$(date +%Y%m%d).tar \
  umbrella-pdf-extraction:latest \
  umbrella-sentiment-analysis:latest \
  umbrella-rag-scraper:latest \
  umbrella-chatbot:latest \
  umbrella-api-gateway:latest
```

### 5. AWS Configuration
```bash
# Backup AWS configuration
aws configure export-credentials \
  > aws-credentials-$(date +%Y%m%d).json

# Export security group rules
aws ec2 describe-security-groups \
  --group-ids <security-group-id> \
  > security-groups-$(date +%Y%m%d).json
```

## Recovery Procedures

### 1. System Recovery

#### Full System Recovery
```bash
# Stop all services
docker-compose down

# Restore configuration files
tar xzf docker-compose-backup-*.tar.gz
cp .env.backup.* .env

# Load container images
docker load -i umbrella-images-*.tar

# Start services
docker-compose up -d
```

#### Partial Service Recovery
```bash
# Restart specific service
docker-compose up -d --no-deps <service_name>

# Verify service health
./scripts/health_check.sh
```

### 2. Data Recovery

#### Vector Database Recovery
```bash
# Stop vector database service
docker-compose stop vector_db

# Restore vector database files
tar xzf vector-db-backup-*.tar.gz -C ./data/

# Start service
docker-compose start vector_db
```

#### MongoDB Recovery
```bash
# Stop MongoDB service
docker-compose stop mongodb

# Restore MongoDB backup
docker cp \
  ./backups/mongodb/mongodb-* \
  mongodb:/backup/

docker exec mongodb mongorestore \
  --drop /backup/mongodb-*

# Start service
docker-compose start mongodb
```

### 3. Configuration Recovery

#### API Keys and Secrets
```bash
# Restore AWS Secrets
aws secretsmanager update-secret \
  --secret-id umbrella/gemini/api-keys \
  --secret-string file://secrets_backup_*.json

# Verify secrets
aws secretsmanager get-secret-value \
  --secret-id umbrella/gemini/api-keys
```

#### AWS Configuration
```bash
# Restore AWS credentials
aws configure import \
  --csv file://aws-credentials-*.json

# Restore security group rules
aws ec2 update-security-group-rule-descriptions-ingress \
  --group-id <security-group-id> \
  --ip-permissions file://security-groups-*.json
```

## Automated Backup Scripts

### Daily Backup Script
```bash
#!/bin/bash
# /usr/local/bin/umbrella-backup.sh

# Set backup directory
BACKUP_DIR="/backup/umbrella"
DATE=$(date +%Y%m%d)

# Create backup directory
mkdir -p $BACKUP_DIR/$DATE

# Backup configurations
cp .env $BACKUP_DIR/$DATE/
tar czf $BACKUP_DIR/$DATE/docker-compose.tar.gz docker-compose*.yml

# Backup data
tar czf $BACKUP_DIR/$DATE/vector-db.tar.gz ./data/vector_db/
docker exec mongodb mongodump --out /backup/mongodb-$DATE

# Backup logs
sudo tar czf $BACKUP_DIR/$DATE/logs.tar.gz /var/log/umbrella/

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR -type d -mtime +7 -exec rm -rf {} +
```

### Backup Verification Script
```bash
#!/bin/bash
# /usr/local/bin/verify-backup.sh

BACKUP_DIR="/backup/umbrella"
DATE=$(date +%Y%m%d)

# Verify backup files exist
for file in env docker-compose.tar.gz vector-db.tar.gz logs.tar.gz; do
  if [ ! -f "$BACKUP_DIR/$DATE/$file" ]; then
    echo "ERROR: Missing backup file: $file"
    exit 1
  fi
done

# Verify MongoDB backup
if ! docker exec mongodb mongodump --out /backup/test-restore; then
  echo "ERROR: MongoDB backup verification failed"
  exit 1
fi

echo "Backup verification completed successfully"
```

## Disaster Recovery Plan

### 1. Initial Response
1. Assess the scope of the failure
2. Notify relevant team members
3. Document the incident timeline

### 2. Recovery Steps

#### Critical Service Recovery
1. Restore API Gateway and core services first:
   ```bash
   docker-compose up -d api_gateway pdf_extraction
   ```

2. Verify core functionality:
   ```bash
   ./scripts/health_check.sh
   ```

3. Restore remaining services:
   ```bash
   docker-compose up -d
   ```

#### Data Consistency Check
1. Verify vector database integrity:
   ```bash
   docker exec vector_db python3 -c "
   from chromadb import Client
   client = Client()
   print(client.heartbeat())
   "
   ```

2. Check MongoDB collections:
   ```bash
   docker exec mongodb mongosh --eval "
   db.getSiblingDB('umbrella').getCollectionNames()
   "
   ```

### 3. Post-Recovery Actions

1. Update DNS/routing if needed:
   ```bash
   aws route53 change-resource-record-sets \
     --hosted-zone-id <zone-id> \
     --change-batch file://dns-updates.json
   ```

2. Verify all services:
   ```bash
   ./scripts/health_check.sh
   python3 scripts/collect_metrics.py --verify
   ```

3. Generate incident report:
   ```bash
   python3 scripts/generate_incident_report.py \
     --start-time "$(date -d '1 hour ago' -Iseconds)" \
     --end-time "$(date -Iseconds)"
   ```

## Best Practices

1. **Regular Testing**
   - Test backup restoration monthly
   - Verify backup integrity daily
   - Practice disaster recovery scenarios quarterly

2. **Documentation**
   - Keep backup logs
   - Document all recovery attempts
   - Update procedures based on lessons learned

3. **Security**
   - Encrypt backup files
   - Secure backup storage
   - Limit access to backup locations

4. **Monitoring**
   - Monitor backup success/failure
   - Track backup size trends
   - Alert on backup issues

## Support

For backup and recovery assistance:
1. Check backup logs: `tail -f /var/log/umbrella/backup.log`
2. Review automated test results
3. Contact the support team with backup verification reports 