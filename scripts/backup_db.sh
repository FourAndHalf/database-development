#!/bin/bash
# scripts/backup_db.sh

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="backup_${TIMESTAMP}.sql"
S3_PATH="s3://${AWS_S3_BUCKET_NAME}/backups/db/${BACKUP_FILE}"

echo "Starting database backup: ${BACKUP_FILE}"

# 1. Generate the dump using the Docker container
docker exec nexus_postgres pg_dump -U nexus nexus_db > "/tmp/${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "Backup successful. Uploading to S3..."
    
    # 2. Upload to S3 (assuming aws-cli is available on the host)
    aws s3 cp "/tmp/${BACKUP_FILE}" "${S3_PATH}"
    
    if [ $? -eq 0 ]; then
        echo "Upload successful: ${S3_PATH}"
        rm "/tmp/${BACKUP_FILE}"
    else
        echo "Error: S3 upload failed."
        exit 1
    fi
else
    echo "Error: Database dump failed."
    exit 1
fi
