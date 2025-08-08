#!/bin/bash

# Verba Restore Script
# Restores a Verba backup to the current Weaviate instance

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if backup ID is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_id>"
    echo ""
    echo "Available backups:"
    if [ -f "../backups/latest_backup_id.txt" ]; then
        LATEST=$(cat ../backups/latest_backup_id.txt)
        echo "   Latest: $LATEST"
    fi
    ls -1 ../backups/ 2>/dev/null | grep "verba-backup-" || echo "   No backups found"
    exit 1
fi

BACKUP_ID=$1

echo "🔄 Starting Verba restore process..."
echo "📋 Backup ID: $BACKUP_ID"

# Check if Weaviate is running
if ! curl -f http://localhost:8080/v1/meta > /dev/null 2>&1; then
    echo "❌ Weaviate is not running or not accessible at http://localhost:8080"
    echo "💡 Start disaster recovery environment: ./start_disaster_recovery.sh"
    exit 1
fi

# Check if backup exists
if [ ! -d "../backups/$BACKUP_ID" ]; then
    echo "❌ Backup not found: ../backups/$BACKUP_ID"
    echo "📋 Available backups:"
    ls -1 ../backups/ 2>/dev/null | grep "verba-backup-" || echo "   No backups found"
    exit 1
fi

echo "📦 Restoring backup..."

# Restore backup using REST API
RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$BACKUP_ID\"}" \
  http://localhost:8080/v1/backups/filesystem/$BACKUP_ID/restore)

echo "📊 Restore response: $RESPONSE"

# Wait for restore to complete
echo "⏳ Waiting for restore to complete..."
sleep 10

# Check restore status
STATUS_RESPONSE=$(curl -s http://localhost:8080/v1/backups/filesystem/$BACKUP_ID/restore)
STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')

if [ "$STATUS" = "SUCCESS" ]; then
    echo "✅ Restore completed successfully!"
    
    # Verify data
    echo "🔍 Verifying restored data..."
    
    # Count collections
    COLLECTIONS=$(curl -s http://localhost:8080/v1/schema | jq '.classes | length')
    echo "📚 Collections restored: $COLLECTIONS"
    
    # Count documents
    DOCS=$(curl -s -X POST http://localhost:8080/v1/graphql \
      -H "Content-Type: application/json" \
      -d '{"query": "{ Aggregate { VERBA_DOCUMENTS { meta { count } } } }"}' | \
      jq '.data.Aggregate.VERBA_DOCUMENTS[0].meta.count')
    
    echo "📄 Documents restored: $DOCS"
    
    # Expected document count
    EXPECTED=178
    if [ "$DOCS" -eq "$EXPECTED" ]; then
        echo "✅ Document count matches expected: $EXPECTED"
    else
        echo "⚠️  Document count mismatch. Expected: $EXPECTED, Found: $DOCS"
    fi
    
else
    echo "❌ Restore failed with status: $STATUS"
    echo "📊 Full response: $STATUS_RESPONSE"
    exit 1
fi

echo ""
echo "🎉 Restore process completed!"
echo "💡 Next steps:"
echo "   1. Run: ./verify_data.py to perform detailed verification"
echo "   2. Run: ./query_sample_data.py to test queries"
echo "   3. Access Weaviate console: http://localhost:8080/v1/console"
