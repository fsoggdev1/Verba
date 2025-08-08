#!/bin/bash

# Clear Auto-Created Collections Script
# Removes empty collections that Verba automatically creates, which block backup restore

set -e

echo "🧹 Clearing Auto-Created Verba Collections"
echo "=========================================="

# Check if Weaviate is running
if ! curl -f http://localhost:8080/v1/meta > /dev/null 2>&1; then
    echo "❌ Weaviate is not running or not accessible at http://localhost:8080"
    exit 1
fi

# Get current collections
echo "🔍 Checking current collections..."
COLLECTIONS=$(curl -s http://localhost:8080/v1/schema | jq -r '.classes[]?.class' 2>/dev/null)

if [ -z "$COLLECTIONS" ]; then
    echo "✅ No collections found - database is already clean"
    exit 0
fi

echo "📋 Found collections:"
echo "$COLLECTIONS" | sed 's/^/   - /'

echo ""
echo "🗑️ Removing auto-created collections..."

# List of collections that Verba typically auto-creates
AUTO_COLLECTIONS=(
    "VERBA_DOCUMENTS"
    "VERBA_SUGGESTIONS" 
    "VERBA_Embedding_all_MiniLM_L6_v2"
    "VERBA_CONFIGURATION"
    "VERBA_Embedding_embed_english_light_v3_0"
    "VERBA_Embedding_all_mpnet_base_v2"
    "VERBA_Embedding_Couldn_t_connect_to_Ollama_http___host_docker_internal_11434"
)

DELETED_COUNT=0

for collection in "${AUTO_COLLECTIONS[@]}"; do
    # Check if collection exists
    if echo "$COLLECTIONS" | grep -q "^$collection$"; then
        echo "   Deleting: $collection"
        
        # Delete the collection
        RESPONSE=$(curl -s -w "%{http_code}" -X DELETE http://localhost:8080/v1/schema/$collection)
        HTTP_CODE="${RESPONSE: -3}"
        
        if [ "$HTTP_CODE" = "200" ]; then
            echo "   ✅ Successfully deleted: $collection"
            ((DELETED_COUNT++))
        else
            echo "   ⚠️  Failed to delete: $collection (HTTP $HTTP_CODE)"
        fi
    fi
done

echo ""
echo "📊 Summary:"
echo "   Collections deleted: $DELETED_COUNT"

# Verify clean state
REMAINING=$(curl -s http://localhost:8080/v1/schema | jq -r '.classes | length')
echo "   Collections remaining: $REMAINING"

if [ "$REMAINING" -eq 0 ]; then
    echo "✅ Database is now clean and ready for backup restore"
else
    echo "⚠️  Some collections remain - check if they contain important data"
    echo "📋 Remaining collections:"
    curl -s http://localhost:8080/v1/schema | jq -r '.classes[] | .class' | sed 's/^/   - /'
fi

echo ""
echo "💡 You can now proceed with backup restore using:"
echo "   ./restore_verba.sh <backup_id>"
