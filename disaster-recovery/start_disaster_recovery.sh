#!/bin/bash

# Verba Disaster Recovery Startup Script
# Starts a fresh Weaviate instance for disaster recovery

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚨 Starting Verba Disaster Recovery Process..."

# Stop existing Verba services
echo "🛑 Stopping existing Verba services..."
cd ..
docker compose down

# Start disaster recovery container with specific project name
echo "🚀 Starting disaster recovery Weaviate container..."
cd disaster-recovery
docker compose -p verba-dr -f docker-compose.disaster-recovery.yml up -d

# Wait for Weaviate to be ready
echo "⏳ Waiting for Weaviate to be ready..."
sleep 30

# Check if Weaviate is ready
for i in {1..10}; do
    if curl -f http://localhost:8080/v1/meta > /dev/null 2>&1; then
        echo "✅ Weaviate disaster recovery instance is ready"
        break
    fi
    echo "⏳ Waiting... (attempt $i/10)"
    sleep 10
done

# Verify Weaviate is accessible
if ! curl -f http://localhost:8080/v1/meta > /dev/null 2>&1; then
    echo "❌ Weaviate disaster recovery instance failed to start"
    exit 1
fi

# Check if it's a fresh instance (no collections)
COLLECTIONS=$(curl -s http://localhost:8080/v1/schema | jq '.classes | length')
if [ "$COLLECTIONS" -eq 0 ]; then
    echo "✅ Fresh Weaviate instance confirmed (no existing collections)"
else
    echo "⚠️  Warning: Weaviate instance has $COLLECTIONS existing collections"
fi

echo ""
echo "🎉 Disaster recovery environment ready!"
echo "📋 Container: weaviate-disaster-recovery"
echo "🌐 URL: http://localhost:8080"
echo "💡 Next steps:"
echo "   1. Run: ./restore_verba.sh <backup_id>"
echo "   2. Or run: ./list_backups.sh to see available backups"
