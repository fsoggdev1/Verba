#!/usr/bin/env python3
import weaviate
import datetime
import sys
import json

def create_backup():
    try:
        client = weaviate.Client("http://localhost:8080")
        
        # Generate backup ID with timestamp
        backup_id = f"verba-backup-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        print(f"🚀 Creating backup: {backup_id}")
        
        # Create backup
        result = client.backup.create(
            backup_id=backup_id,
            backend="filesystem",
            wait_for_completion=True,
        )
        
        print(f"✅ Backup completed successfully!")
        print(f"📋 Backup ID: {backup_id}")
        print(f"📊 Status: {result['status']}")
        
        # Verify collections backed up
        if 'classes' in result:
            print(f"📚 Collections backed up: {len(result['classes'])}")
            for collection in result['classes']:
                print(f"   - {collection}")
        
        return backup_id
        
    except Exception as e:
        print(f"❌ Backup failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    backup_id = create_backup()
    print(f"\n💡 To restore this backup, use: {backup_id}")
