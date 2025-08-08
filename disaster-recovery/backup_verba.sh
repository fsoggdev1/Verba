#!/bin/bash

# Verba Backup Script
# Creates a backup of the current Verba Weaviate database

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_ID="verba-backup-$(date +%Y%m%d-%H%M%S)"

echo "🚀 Starting Verba backup process..."
echo "📋 Backup ID: $BACKUP_ID"

# Check if Weaviate is running
if ! curl -f http://localhost:8080/v1/meta > /dev/null 2>&1; then
    echo "❌ Weaviate is not running or not accessible at http://localhost:8080"
    echo "💡 Make sure Verba is running: docker compose up -d"
    exit 1
fi

# Check if backup module is enabled
if ! curl -s http://localhost:8080/v1/meta | grep -q "backup-filesystem"; then
    echo "❌ backup-filesystem module is not enabled"
    echo "💡 Please enable the backup module in your docker-compose.yml"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p ../backups

echo "📦 Creating backup..."

# Create backup using REST API
RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$BACKUP_ID\"}" \
  http://localhost:8080/v1/backups/filesystem)

echo "📊 Backup response: $RESPONSE"

# Wait for backup to complete
echo "⏳ Waiting for backup to complete..."
sleep 5

# Check backup status
STATUS_RESPONSE=$(curl -s http://localhost:8080/v1/backups/filesystem/$BACKUP_ID)
STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')

if [ "$STATUS" = "SUCCESS" ]; then
    echo "✅ Backup completed successfully!"
    echo "📋 Backup ID: $BACKUP_ID"
    echo "📁 Backup location: ../backups/$BACKUP_ID"
    
    # Show backup files
    echo "📄 Backup files:"
    ls -la ../backups/$BACKUP_ID/ 2>/dev/null || echo "   (Backup files not yet visible from host)"
    
    # Save backup ID for easy reference
    echo $BACKUP_ID > ../backups/latest_backup_id.txt
    echo "💾 Latest backup ID saved to ../backups/latest_backup_id.txt"
    
else
    echo "❌ Backup failed with status: $STATUS"
    echo "📊 Full response: $STATUS_RESPONSE"
    exit 1
fi

echo ""
echo "🎉 Backup process completed!"
echo "💡 To restore this backup, use: ./restore_verba.sh $BACKUP_ID"
