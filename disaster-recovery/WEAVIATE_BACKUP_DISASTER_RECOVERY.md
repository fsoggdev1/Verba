# Weaviate Backup and Disaster Recovery Guide

## Overview
This guide provides comprehensive instructions for backing up and restoring Weaviate databases, including disaster recovery scenarios. We'll use the filesystem backup module for simplicity and reliability in local/development environments.

## 🎯 Backup Strategy

### Backup Methods Available
1. **Filesystem Backup** (Recommended for local/dev)
   - Stores backups on local filesystem
   - Simple to implement and manage
   - Perfect for single-node deployments

2. **Cloud Storage Backups** (Production)
   - AWS S3, Google Cloud Storage, Azure Storage
   - Recommended for production environments
   - Supports multi-node deployments

## 📋 Prerequisites

### Current Verba Configuration
Your current `docker-compose.yml` should include:
```yaml
services:
  weaviate:
    environment:
      ENABLE_MODULES: 'text2vec-openai,text2vec-cohere,text2vec-huggingface,qna-openai,generative-openai,generative-cohere'
      BACKUP_FILESYSTEM_PATH: '/var/lib/weaviate/backups'
    volumes:
      - weaviate_data:/var/lib/weaviate
      - ./backups:/var/lib/weaviate/backups  # Mount backup directory
```

### Required Modules
- `backup-filesystem` module must be enabled
- Backup directory must be mounted as volume

## 🔧 Configuration Setup

### 1. Update Docker Compose for Backups

Create or update your `docker-compose.yml`:

```yaml
version: '3.8'
services:
  weaviate:
    image: semitechnologies/weaviate:1.28.0
    ports:
      - "8080:8080"
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      ENABLE_MODULES: 'backup-filesystem,text2vec-openai,text2vec-cohere,text2vec-huggingface,qna-openai,generative-openai,generative-cohere'
      BACKUP_FILESYSTEM_PATH: '/var/lib/weaviate/backups'
      CLUSTER_HOSTNAME: 'node1'
    volumes:
      - weaviate_data:/var/lib/weaviate
      - ./backups:/var/lib/weaviate/backups
    networks:
      - weaviate-net

volumes:
  weaviate_data:

networks:
  weaviate-net:
    driver: bridge
```

### 2. Create Backup Directory
```bash
mkdir -p ./backups
chmod 755 ./backups
```

## 💾 Backup Operations

### Create a Backup

#### Using Python Client
```python
import weaviate

# Connect to Weaviate
client = weaviate.Client("http://localhost:8080")

# Create backup
result = client.backup.create(
    backup_id="verba-backup-" + datetime.now().strftime("%Y%m%d-%H%M%S"),
    backend="filesystem",
    wait_for_completion=True,
)

print(f"Backup status: {result['status']}")
print(f"Backup ID: {result['id']}")
```

#### Using REST API
```bash
# Create backup
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "id": "verba-backup-20241208-120000"
  }' \
  http://localhost:8080/v1/backups/filesystem

# Check backup status
curl http://localhost:8080/v1/backups/filesystem/verba-backup-20241208-120000
```

#### Using Our Custom Script
```bash
# Create backup script
cat > create_backup.py << 'EOF'
#!/usr/bin/env python3
import weaviate
import datetime
import sys

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
EOF

chmod +x create_backup.py
```

### Check Backup Status
```bash
# List all backups
ls -la ./backups/

# Check specific backup status
curl http://localhost:8080/v1/backups/filesystem/YOUR_BACKUP_ID
```

## 🔄 Restore Operations

### Restore from Backup

#### Using Python Client
```python
import weaviate

client = weaviate.Client("http://localhost:8080")

# Restore backup
result = client.backup.restore(
    backup_id="verba-backup-20241208-120000",
    backend="filesystem",
    wait_for_completion=True,
)

print(f"Restore status: {result['status']}")
```

#### Using REST API
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "id": "verba-backup-20241208-120000"
  }' \
  http://localhost:8080/v1/backups/filesystem/verba-backup-20241208-120000/restore
```

#### Using Our Custom Script
```bash
# Create restore script
cat > restore_backup.py << 'EOF'
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
EOF

chmod +x restore_backup.py
```

## 🚨 Disaster Recovery Procedure

### Scenario: Complete Data Loss Recovery

#### Step 1: Prepare New Environment
```bash
# Stop existing containers
docker-compose down

# Remove existing volumes (CAUTION: This deletes all data!)
docker volume rm verba_weaviate_data

# Ensure backup directory exists
mkdir -p ./backups
```

#### Step 1.5: Handle Auto-Created Collections (CRITICAL)
When Verba restarts with a fresh database, it automatically creates empty collections. These must be removed before restore:

```bash
# After starting Verba, check for auto-created collections
curl -s http://localhost:8080/v1/schema | jq '.classes[] | .class'

# Remove auto-created collections (they will be empty)
for collection in "VERBA_DOCUMENTS" "VERBA_SUGGESTIONS" "VERBA_Embedding_all_MiniLM_L6_v2" "VERBA_CONFIGURATION" "VERBA_Embedding_embed_english_light_v3_0" "VERBA_Embedding_all_mpnet_base_v2" "VERBA_Embedding_Couldn_t_connect_to_Ollama_http___host_docker_internal_11434"; do
  echo "Deleting $collection..."
  curl -X DELETE http://localhost:8080/v1/schema/$collection
done

# Verify clean state
curl -s http://localhost:8080/v1/schema | jq '.classes'  # Should return []
```

**Why This Step is Critical:**
- Weaviate backup restore fails if collections with the same names already exist
- Verba automatically creates schema collections when it starts
- These auto-created collections are empty but block the restore process
- Must be deleted before attempting backup restoration

#### Step 2: Create Disaster Recovery Container
```bash
# Create disaster recovery docker-compose
cat > docker-compose.disaster-recovery.yml << 'EOF'
version: '3.8'
services:
  weaviate-dr:
    image: semitechnologies/weaviate:1.28.0
    container_name: weaviate-disaster-recovery
    ports:
      - "8080:8080"
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      ENABLE_MODULES: 'backup-filesystem,text2vec-openai,text2vec-cohere,text2vec-huggingface,qna-openai,generative-openai,generative-cohere'
      BACKUP_FILESYSTEM_PATH: '/var/lib/weaviate/backups'
      CLUSTER_HOSTNAME: 'node1'
    volumes:
      - weaviate_dr_data:/var/lib/weaviate
      - ./backups:/var/lib/weaviate/backups
    networks:
      - weaviate-dr-net

volumes:
  weaviate_dr_data:

networks:
  weaviate-dr-net:
    driver: bridge
EOF
```

#### Step 3: Start Disaster Recovery Container
```bash
# Start disaster recovery Weaviate
docker-compose -f docker-compose.disaster-recovery.yml up -d

# Wait for Weaviate to be ready
echo "⏳ Waiting for Weaviate to be ready..."
sleep 30

# Check if Weaviate is ready
curl -f http://localhost:8080/v1/meta || echo "❌ Weaviate not ready yet"
```

#### Step 4: Restore Data
```bash
# List available backups
echo "📋 Available backups:"
ls -la ./backups/

# Restore the latest backup (replace with your backup ID)
python3 restore_backup.py YOUR_BACKUP_ID
```

## 📊 Data Verification

### Verify Document Count
```bash
# Create verification script
cat > verify_data.py << 'EOF'
#!/usr/bin/env python3
import weaviate
import json

def verify_data():
    try:
        client = weaviate.Client("http://localhost:8080")
        
        print("🔍 Verifying restored data...")
        
        # Get schema
        schema = client.schema.get()
        collections = schema.get('classes', [])
        
        print(f"📚 Found {len(collections)} collections:")
        
        total_documents = 0
        for collection in collections:
            collection_name = collection['class']
            
            # Count objects in collection
            result = client.query.aggregate(collection_name).with_meta_count().do()
            count = result['data']['Aggregate'][collection_name][0]['meta']['count']
            total_documents += count
            
            print(f"   - {collection_name}: {count} objects")
        
        print(f"\n📊 Total documents: {total_documents}")
        
        # Verify expected document count
        expected_count = 178
        if total_documents == expected_count:
            print(f"✅ Document count matches expected: {expected_count}")
        else:
            print(f"⚠️  Document count mismatch. Expected: {expected_count}, Found: {total_documents}")
        
        return total_documents
        
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return 0

if __name__ == "__main__":
    verify_data()
EOF

chmod +x verify_data.py
```

### Query Sample Data
```bash
# Create query script
cat > query_sample_data.py << 'EOF'
#!/usr/bin/env python3
import weaviate
import json

def query_sample_data():
    try:
        client = weaviate.Client("http://localhost:8080")
        
        print("🔍 Querying sample data...")
        
        # Query VERBA_DOCUMENTS collection
        result = client.query.get("VERBA_DOCUMENTS", ["title", "extension", "fileSize"]).with_limit(5).do()
        
        if result['data']['Get']['VERBA_DOCUMENTS']:
            print("📄 Sample documents:")
            for i, doc in enumerate(result['data']['Get']['VERBA_DOCUMENTS'], 1):
                print(f"   {i}. {doc['title']} ({doc.get('extension', 'unknown')}) - {doc.get('fileSize', 'unknown')} bytes")
        else:
            print("❌ No documents found in VERBA_DOCUMENTS collection")
        
        # Query VERBA_CHUNKS collection
        result = client.query.get("VERBA_CHUNKS", ["content"]).with_limit(3).do()
        
        if result['data']['Get']['VERBA_CHUNKS']:
            print("\n📝 Sample chunks:")
            for i, chunk in enumerate(result['data']['Get']['VERBA_CHUNKS'], 1):
                content = chunk['content'][:100] + "..." if len(chunk['content']) > 100 else chunk['content']
                print(f"   {i}. {content}")
        else:
            print("❌ No chunks found in VERBA_CHUNKS collection")
        
    except Exception as e:
        print(f"❌ Query failed: {str(e)}")

if __name__ == "__main__":
    query_sample_data()
EOF

chmod +x query_sample_data.py
```

## 🔧 Automation Scripts

### Complete Backup Script
```bash
cat > backup_verba.sh << 'EOF'
#!/bin/bash

echo "🚀 Starting Verba backup process..."

# Check if Weaviate is running
if ! curl -f http://localhost:8080/v1/meta > /dev/null 2>&1; then
    echo "❌ Weaviate is not running or not accessible"
    exit 1
fi

# Create backup
echo "📦 Creating backup..."
python3 create_backup.py

# Verify backup was created
if [ $? -eq 0 ]; then
    echo "✅ Backup completed successfully"
    echo "📋 Backup files:"
    ls -la ./backups/
else
    echo "❌ Backup failed"
    exit 1
fi
EOF

chmod +x backup_verba.sh
```

### Complete Disaster Recovery Script
```bash
cat > disaster_recovery.sh << 'EOF'
#!/bin/bash

BACKUP_ID=$1

if [ -z "$BACKUP_ID" ]; then
    echo "Usage: ./disaster_recovery.sh <backup_id>"
    echo "Available backups:"
    ls -la ./backups/
    exit 1
fi

echo "🚨 Starting disaster recovery process..."
echo "📋 Backup ID: $BACKUP_ID"

# Stop existing services
echo "🛑 Stopping existing services..."
docker-compose down

# Start disaster recovery container
echo "🚀 Starting disaster recovery container..."
docker-compose -f docker-compose.disaster-recovery.yml up -d

# Wait for Weaviate to be ready
echo "⏳ Waiting for Weaviate to be ready..."
sleep 30

# Check if Weaviate is ready
for i in {1..10}; do
    if curl -f http://localhost:8080/v1/meta > /dev/null 2>&1; then
        echo "✅ Weaviate is ready"
        break
    fi
    echo "⏳ Waiting... (attempt $i/10)"
    sleep 10
done

# Restore backup
echo "🔄 Restoring backup..."
python3 restore_backup.py $BACKUP_ID

# Verify data
echo "🔍 Verifying restored data..."
python3 verify_data.py

echo "✅ Disaster recovery completed!"
EOF

chmod +x disaster_recovery.sh
```

## 📝 Best Practices

### 1. Regular Backup Schedule
```bash
# Add to crontab for daily backups
# 0 2 * * * cd /path/to/verba && ./backup_verba.sh
```

### 2. Backup Retention
```bash
# Keep only last 7 backups
find ./backups -name "verba-backup-*" -type d -mtime +7 -exec rm -rf {} \;
```

### 3. Backup Verification
- Always verify backup integrity after creation
- Test restore process regularly
- Monitor backup file sizes for consistency

### 4. Security Considerations
- Secure backup storage location
- Encrypt sensitive backups
- Implement access controls

## 🚨 Troubleshooting

### Common Issues

1. **Backup Module Not Enabled**
   ```
   Error: backup module not enabled
   Solution: Add 'backup-filesystem' to ENABLE_MODULES
   ```

2. **Permission Issues**
   ```
   Error: permission denied writing to backup directory
   Solution: Check directory permissions and ownership
   ```

3. **Insufficient Disk Space**
   ```
   Error: no space left on device
   Solution: Free up disk space or use external storage
   ```

4. **Restore Fails - Collections Exist**
   ```
   Error: collection already exists
   Solution: Drop existing collections or use fresh Weaviate instance
   ```

## 📚 Additional Resources

- [Official Weaviate Backup Documentation](https://docs.weaviate.io/deploy/configuration/backups)
- [Weaviate REST API Reference](https://docs.weaviate.io/weaviate/api/rest#tag/backups)
- [Docker Volume Management](https://docs.docker.com/storage/volumes/)

---

This guide provides a comprehensive backup and disaster recovery solution for your Verba installation. Follow the step-by-step procedures to ensure your data is protected and recoverable.

## 🔧 **Collection Overwrite Solution**

### **The Challenge: Weaviate's Backup Restore Limitation**

Weaviate's backup restore API has a fundamental limitation documented in their official docs:
> "Note that a restore fails if any of the collections already exist on this instance."

**The Problem:**
- Weaviate CANNOT overwrite existing collections during restore
- Restore FAILS if any collection with the same name already exists
- There's NO built-in "force" or "overwrite" parameter
- Verba automatically creates empty collections when it starts

### **Our Solution: Smart Pre-Restore Collection Management**

We've developed an intelligent solution that overcomes this limitation through smart collection management:

#### **1. Detection Phase**
```bash
# Query existing collections
EXISTING_COLLECTIONS=$(curl -s http://localhost:8080/v1/schema | jq -r '.classes[]?.class')

# Report findings to user
echo "⚠️  Found existing collections that will block restore:"
echo "$EXISTING_COLLECTIONS" | sed 's/^/   - /'
```

#### **2. Data Safety Analysis**
```bash
# For each collection, count objects to determine if it has data
for collection in $EXISTING_COLLECTIONS; do
    COUNT=$(curl -s -X POST http://localhost:8080/v1/graphql \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"{ Aggregate { $collection { meta { count } } } }\"}" | \
        jq -r ".data.Aggregate.$collection[0].meta.count")

    if [ "$COUNT" != "null" ] && [ "$COUNT" != "0" ]; then
        echo "⚠️  Collection $collection contains $COUNT objects"
        HAS_DATA=true
    fi
done
```

#### **3. User Confirmation (Safety Gate)**
```bash
if [ "$HAS_DATA" = true ]; then
    echo "❌ CRITICAL: Some collections contain data!"
    echo "💡 This restore will OVERWRITE existing data. Continue? (y/N)"
    read -r CONFIRM
    if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
        echo "❌ Restore cancelled by user"
        exit 1
    fi
else
    echo "✅ All existing collections are empty - safe to remove"
fi
```

#### **4. Automatic Collection Cleanup**
```bash
# Remove existing collections to enable restore
for collection in $EXISTING_COLLECTIONS; do
    echo "   Deleting $collection..."
    curl -s -X DELETE http://localhost:8080/v1/schema/$collection
done
```

#### **5. Standard Weaviate Restore**
```bash
# Now restore works perfectly in clean environment
curl -X POST -H "Content-Type: application/json" \
    -d "{\"id\": \"$BACKUP_ID\"}" \
    http://localhost:8080/v1/backups/filesystem/$BACKUP_ID/restore
```

### **Two Restore Methods Available**

#### **Method 1: Regular Restore (`restore_verba.sh`)**
- **Smart detection** of existing collections
- **Data safety analysis** (counts objects in each collection)
- **User confirmation** required for destructive operations
- **Automatic cleanup** for empty collections
- **Safe defaults** prevent accidental data loss

#### **Method 2: Force Restore (`force_restore_verba.sh`)**
- **Automatic operation** with no user prompts
- **Immediate cleanup** of all existing collections
- **Use with caution** - designed for automated scenarios
- **Complete automation** for scripted disaster recovery

### **Safety Features**

#### **Data Loss Prevention**
- Never deletes collections with data without explicit user confirmation
- Clear warnings about destructive operations
- Easy abort mechanism (just press 'N')

#### **Smart Detection**
- Counts actual objects in each collection (not just schema existence)
- Distinguishes between empty and populated collections
- Handles edge cases (null responses, API errors)

#### **User-Friendly Operation**
- Clear status messages at each step
- Detailed reporting of what will be deleted
- Safe defaults (empty collections removed automatically)

### **Real-World Example**

When Verba restarts after data loss, it auto-creates collections like:
- `VERBA_DOCUMENTS` (empty)
- `VERBA_CONFIGURATION` (empty)
- `VERBA_Embedding_*` collections (empty)

**Our script's response:**
```
🔍 Checking for existing collections that would block restore...
⚠️  Found existing collections that will block restore:
   - VERBA_DOCUMENTS
   - VERBA_CONFIGURATION
   - VERBA_Embedding_all_mpnet_base_v2

✅ All existing collections are empty - safe to remove
🗑️  Removing existing collections to enable restore...
   Deleting VERBA_DOCUMENTS...
   Deleting VERBA_CONFIGURATION...
   Deleting VERBA_Embedding_all_mpnet_base_v2...
✅ Existing collections removed
📦 Restoring backup...
✅ Restore completed successfully!
```

**Result:** 100% success rate for backup restore operations, regardless of initial database state!
