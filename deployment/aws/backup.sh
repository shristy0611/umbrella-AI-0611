#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Get timestamp for backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup"
S3_BUCKET="s3://umbrella-ai-backups-${BUCKET_SUFFIX}"

echo "Starting UMBRELLA-AI backup process..."
echo "======================================"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Function to backup a service's data
backup_service() {
    local service=$1
    local container=$2
    local data_path=$3
    
    echo -n "Backing up $service... "
    
    # Create tar archive
    if docker run --rm --volumes-from $container \
        -v $BACKUP_DIR:/backup ubuntu \
        tar czf /backup/${service}_${TIMESTAMP}.tar.gz $data_path; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}Failed${NC}"
        return 1
    fi
}

# Backup MongoDB
backup_service "mongodb" "mongodb" "/data/db"

# Backup Vector DB
backup_service "vector_db" "vector_db" "/data"

# Backup Redis
backup_service "redis" "redis" "/data"

# Backup RabbitMQ
backup_service "rabbitmq" "rabbitmq" "/var/lib/rabbitmq"

# Create metadata file
cat > $BACKUP_DIR/metadata.json << EOF
{
    "timestamp": "$TIMESTAMP",
    "services": [
        "mongodb",
        "vector_db",
        "redis",
        "rabbitmq"
    ],
    "environment": "production"
}
EOF

# Compress all backups into a single archive
echo -n "Creating final backup archive... "
cd $BACKUP_DIR
if tar czf umbrella_backup_${TIMESTAMP}.tar.gz \
    *.tar.gz \
    metadata.json; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}Failed${NC}"
    exit 1
fi

# Upload to S3
echo -n "Uploading to S3... "
if aws s3 cp umbrella_backup_${TIMESTAMP}.tar.gz \
    $S3_BUCKET/backups/umbrella_backup_${TIMESTAMP}.tar.gz; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}Failed${NC}"
    exit 1
fi

# Clean up local backup files
echo -n "Cleaning up local backup files... "
if rm -f $BACKUP_DIR/*.tar.gz $BACKUP_DIR/metadata.json; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}Failed${NC}"
    exit 1
fi

echo -e "\nBackup completed successfully!"
echo "Backup file: umbrella_backup_${TIMESTAMP}.tar.gz"
echo "S3 location: $S3_BUCKET/backups/" 