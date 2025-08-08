#!/bin/bash

# Verba Disaster Recovery Cleanup Script
# Stops disaster recovery environment and optionally restarts normal Verba

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🛑 Stopping Verba Disaster Recovery Environment..."

# Stop disaster recovery containers
docker compose -p verba-dr -f docker-compose.disaster-recovery.yml down

echo "✅ Disaster recovery containers stopped"

# Ask if user wants to restart normal Verba
read -p "🤔 Do you want to restart normal Verba? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting normal Verba..."
    cd ..
    docker compose up -d
    
    echo "⏳ Waiting for Verba to be ready..."
    sleep 30
    
    # Check if Verba is ready
    if curl -f http://localhost:8080/v1/meta > /dev/null 2>&1; then
        echo "✅ Verba is ready at http://localhost:8080"
        echo "🌐 Frontend available at http://localhost:3000"
    else
        echo "⚠️  Verba may still be starting up"
    fi
else
    echo "💡 Normal Verba not started. To start manually:"
    echo "   cd .. && docker compose up -d"
fi

echo ""
echo "🎉 Disaster recovery cleanup completed!"
