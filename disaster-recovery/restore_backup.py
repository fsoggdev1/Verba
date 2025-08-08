#!/usr/bin/env python3
import weaviate
import sys

def restore_backup(backup_id):
    try:
        client = weaviate.Client("http://localhost:8080")
        
        print(f"🔄 Restoring backup: {backup_id}")
        
        # Restore backup
        result = client.backup.restore(
            backup_id=backup_id,
            backend="filesystem",
            wait_for_completion=True,
        )
        
        print(f"✅ Restore completed successfully!")
        print(f"📊 Status: {result['status']}")
        
        # Verify collections restored
        if 'classes' in result:
            print(f"📚 Collections restored: {len(result['classes'])}")
            for collection in result['classes']:
                print(f"   - {collection}")
        
    except Exception as e:
        print(f"❌ Restore failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 restore_backup.py <backup_id>")
        sys.exit(1)
    
    backup_id = sys.argv[1]
    restore_backup(backup_id)
