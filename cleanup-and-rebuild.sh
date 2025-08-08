#!/bin/bash

# Smart Docker build script for Verba
# Usage:
#   ./cleanup-and-rebuild.sh          # Full rebuild (slow)
#   ./cleanup-and-rebuild.sh fast     # Fast rebuild (code changes only)
#   ./cleanup-and-rebuild.sh dev      # Development mode with live reload

MODE=${1:-full}

echo "🚀 Starting Verba build process in '$MODE' mode..."

# Step 1: Stop all containers
echo "🛑 Stopping all containers..."
docker compose down

case $MODE in
  "fast")
    echo "⚡ Fast rebuild mode - rebuilding with cached layers..."

    # Fast rebuild - Docker will use cached layers for unchanged parts
    docker compose up -d --build
    ;;

  "dev")
    echo "🔧 Development mode - mounting source code for live changes..."

    # Use development compose file
    docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
    echo "🌐 Development server with live reload available at http://localhost:8000"
    echo "💡 Code changes will be reflected immediately without rebuild!"
    ;;

  "full")
    echo "🧹 Full rebuild mode - cleaning up and rebuilding everything..."

    # Check disk space before cleanup
    echo "💾 Disk space before cleanup:"
    df -h / | grep -E "Filesystem|/dev/root"

    # Clean up old images (but keep volumes with data)
    echo "🗑️  Cleaning up old Docker images..."
    docker image prune -f

    # Remove old Verba images specifically
    docker images | grep verba-verba | awk '{print $3}' | xargs -r docker rmi -f

    # Check disk space after cleanup
    echo "💾 Disk space after cleanup:"
    df -h / | grep -E "Filesystem|/dev/root"

    # Full rebuild
    echo "🔨 Full rebuild and starting Verba..."
    docker compose up -d --build --force-recreate
    ;;

  *)
    echo "❌ Unknown mode: $MODE"
    echo "Usage: $0 [full|fast|dev]"
    exit 1
    ;;
esac

# Wait for containers to be ready
echo "⏳ Waiting for containers to start..."
sleep 10

# Check container status
echo "📊 Container status:"
docker compose ps

# Show final disk usage
echo "💾 Final disk space:"
df -h / | grep -E "Filesystem|/dev/root"

echo "✅ Build complete!"
echo "🌐 Verba should be available at http://localhost:8000"

# Show usage tips
case $MODE in
  "dev")
    echo ""
    echo "💡 Development Tips:"
    echo "   - Code changes are live-reloaded automatically"
    echo "   - Logs: docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f verba"
    echo "   - Stop: docker compose -f docker-compose.yml -f docker-compose.dev.yml down"
    ;;
  "fast")
    echo ""
    echo "💡 Fast Mode Tips:"
    echo "   - Use this for code changes that don't affect dependencies"
    echo "   - If you change pyproject.toml, use 'full' mode instead"
    ;;
esac
