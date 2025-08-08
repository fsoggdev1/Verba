#!/bin/bash

# Verba Backup List Script
# Lists all available backups with details

set -e

echo "📋 Verba Backup Inventory"
echo "========================"

# Check if backups directory exists
if [ ! -d "../backups" ]; then
    echo "❌ No backups directory found"
    echo "💡 Create your first backup with: ./backup_verba.sh"
    exit 1
fi

# Check if any backups exist
BACKUP_COUNT=$(ls -1 ../backups/ 2>/dev/null | grep -c "verba-backup-" || echo "0")

if [ "$BACKUP_COUNT" -eq 0 ]; then
    echo "❌ No backups found"
    echo "💡 Create your first backup with: ./backup_verba.sh"
    exit 1
fi

echo "📦 Found $BACKUP_COUNT backup(s):"
echo ""

# List backups with details
for backup_dir in ../backups/verba-backup-*; do
    if [ -d "$backup_dir" ]; then
        BACKUP_ID=$(basename "$backup_dir")
        
        # Extract date from backup ID
        DATE_PART=$(echo $BACKUP_ID | sed 's/verba-backup-//')
        FORMATTED_DATE=$(echo $DATE_PART | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)-\([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3 \4:\5:\6/')
        
        # Get backup size
        SIZE=$(du -sh "$backup_dir" 2>/dev/null | cut -f1)
        
        # Check if backup config exists and get status
        if [ -f "$backup_dir/backup_config.json" ]; then
            STATUS=$(jq -r '.status' "$backup_dir/backup_config.json" 2>/dev/null || echo "UNKNOWN")
            COLLECTIONS=$(jq -r '.nodes.node1.classes | length' "$backup_dir/backup_config.json" 2>/dev/null || echo "?")
        else
            STATUS="UNKNOWN"
            COLLECTIONS="?"
        fi
        
        echo "🗂️  $BACKUP_ID"
        echo "   📅 Date: $FORMATTED_DATE"
        echo "   📊 Status: $STATUS"
        echo "   📚 Collections: $COLLECTIONS"
        echo "   💾 Size: $SIZE"
        echo ""
    fi
done

# Show latest backup
if [ -f "../backups/latest_backup_id.txt" ]; then
    LATEST=$(cat ../backups/latest_backup_id.txt)
    echo "⭐ Latest backup: $LATEST"
else
    echo "💡 No latest backup marker found"
fi

echo ""
echo "🔧 Commands:"
echo "   Create backup:  ./backup_verba.sh"
echo "   Restore backup: ./restore_verba.sh <backup_id>"
echo "   Start DR:       ./start_disaster_recovery.sh"
