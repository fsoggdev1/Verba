#!/bin/bash

# Quick restart for code changes only (no rebuild needed)
# This is the fastest way to apply code changes

echo "⚡ Quick restart for code changes..."

# Just restart the verba container (code is mounted as volume)
echo "🔄 Restarting Verba container..."
docker compose restart verba

# Wait a moment for startup
echo "⏳ Waiting for Verba to start..."
sleep 5

# Check status
echo "📊 Container status:"
docker compose ps verba

echo "✅ Quick restart complete!"
echo "🌐 Verba should be available at http://localhost:8000"
echo "💡 This only works when code is mounted as volumes (dev mode or production with volume mounts)"
