#!/bin/bash

# Verba Force Restore Script
# Automatically removes existing collections and restores backup without prompts
# USE WITH CAUTION: This will destroy existing data!

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if backup ID is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_id>"
    echo ""
    echo "⚠️  WARNING: This script will FORCE restore and DESTROY existing data!"
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

echo "💥 FORCE RESTORE MODE - DESTRUCTIVE OPERATION"
echo "============================================="
echo "📋 Backup ID: $BACKUP_ID"
echo "⚠️  This will DESTROY all existing data and restore from backup"
echo ""

# Check if Weaviate is running
if ! curl -f http://localhost:8080/v1/meta > /dev/null 2>&1; then
    echo "❌ Weaviate is not running or not accessible at http://localhost:8080"
    echo "💡 Start Verba: docker compose up -d"
    exit 1
fi

# Check if backup exists
if [ ! -d "../backups/$BACKUP_ID" ]; then
    echo "❌ Backup not found: ../backups/$BACKUP_ID"
    echo "📋 Available backups:"
    ls -1 ../backups/ 2>/dev/null | grep "verba-backup-" || echo "   No backups found"
    exit 1
fi

echo "🗑️  STEP 1: Removing ALL existing collections..."

# Get all existing collections
EXISTING_COLLECTIONS=$(curl -s http://localhost:8080/v1/schema | jq -r '.classes[]?.class' 2>/dev/null)

if [ ! -z "$EXISTING_COLLECTIONS" ]; then
    echo "📋 Found collections to remove:"
    echo "$EXISTING_COLLECTIONS" | sed 's/^/   - /'
    
    # Remove all collections without confirmation
    for collection in $EXISTING_COLLECTIONS; do
        echo "   🗑️  Deleting $collection..."
        curl -s -X DELETE http://localhost:8080/v1/schema/$collection > /dev/null 2>&1
    done
    
    echo "✅ All existing collections removed"
else
    echo "✅ No existing collections found"
fi

# Verify clean state
REMAINING=$(curl -s http://localhost:8080/v1/schema | jq -r '.classes | length')
if [ "$REMAINING" -ne 0 ]; then
    echo "❌ Failed to remove all collections. $REMAINING collections remain."
    exit 1
fi

echo "✅ Database is now clean"
echo ""

echo "📦 STEP 2: Restoring backup..."

# Restore backup using REST API
RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$BACKUP_ID\"}" \
  http://localhost:8080/v1/backups/filesystem/$BACKUP_ID/restore)

echo "📊 Restore initiated: $RESPONSE"

# Wait for restore to complete
echo "⏳ Waiting for restore to complete..."
sleep 10

# Check restore status with retries
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    STATUS_RESPONSE=$(curl -s http://localhost:8080/v1/backups/filesystem/$BACKUP_ID/restore)
    STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
    
    if [ "$STATUS" = "SUCCESS" ]; then
        echo "✅ Restore completed successfully!"
        break
    elif [ "$STATUS" = "FAILED" ]; then
        echo "❌ Restore failed!"
        echo "📊 Error details: $STATUS_RESPONSE"
        exit 1
    else
        echo "⏳ Restore in progress... (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
        sleep 10
        ((RETRY_COUNT++))
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Restore timed out after $((MAX_RETRIES * 10)) seconds"
    exit 1
fi

echo ""
echo "🔍 STEP 3: Verifying restored data..."

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

echo ""
echo "🎉 FORCE RESTORE COMPLETED SUCCESSFULLY!"
echo "========================================"
echo "📊 Summary:"
echo "   📚 Collections: $COLLECTIONS"
echo "   📄 Documents: $DOCS"
echo "   🔗 Verba Frontend: http://localhost:3000"
echo "   🔗 Weaviate API: http://localhost:8080"
echo ""
echo "💡 Next steps:"
echo "   1. Test the Verba frontend at http://localhost:3000"
echo "   2. Run: ./verify_data.py for detailed verification"
echo "   3. Run: ./query_sample_data.py to test search functionality"
