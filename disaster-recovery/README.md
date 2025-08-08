# Verba Disaster Recovery System

This directory contains a complete disaster recovery implementation for Verba's Weaviate database, including backup, restore, and verification tools.

## 🎯 Quick Start

### Create a Backup
```bash
./backup_verba.sh
```

### List Available Backups
```bash
./list_backups.sh
```

### Start Disaster Recovery Environment
```bash
./start_disaster_recovery.sh
```

### Restore from Backup
```bash
./restore_verba.sh <backup_id>
```

### Stop Disaster Recovery
```bash
./stop_disaster_recovery.sh
```

## 📁 Files Overview

### Shell Scripts
- **`backup_verba.sh`** - Creates timestamped backups of current Verba data
- **`start_disaster_recovery.sh`** - Starts fresh Weaviate instance for recovery
- **`restore_verba.sh`** - Restores backup to current Weaviate instance
- **`list_backups.sh`** - Lists all available backups with details
- **`stop_disaster_recovery.sh`** - Stops DR environment and optionally restarts Verba

### Python Scripts
- **`create_backup.py`** - Python-based backup creation (alternative to shell)
- **`restore_backup.py`** - Python-based restore (alternative to shell)
- **`verify_data.py`** - Comprehensive data verification after restore
- **`query_sample_data.py`** - Sample queries to test restored data

### Configuration
- **`docker-compose.disaster-recovery.yml`** - DR Weaviate container configuration
- **`WEAVIATE_BACKUP_DISASTER_RECOVERY.md`** - Comprehensive technical documentation

## 🚀 Usage Examples

### Scenario 1: Regular Backup
```bash
# Create backup before major changes
./backup_verba.sh

# Output:
# 🚀 Starting Verba backup process...
# 📋 Backup ID: verba-backup-20241208-143022
# ✅ Backup completed successfully!
```

### Scenario 2: Complete Disaster Recovery
```bash
# 1. Start disaster recovery environment
./start_disaster_recovery.sh

# 2. List available backups
./list_backups.sh

# 3. Restore latest backup
./restore_verba.sh verba-backup-20241208-143022

# 4. Verify data integrity
./verify_data.py

# 5. Test with sample queries
./query_sample_data.py
```

### Scenario 3: Backup Management
```bash
# List all backups with details
./list_backups.sh

# Output:
# 📋 Verba Backup Inventory
# ========================
# 📦 Found 3 backup(s):
# 
# 🗂️  verba-backup-20241208-143022
#    📅 Date: 2024-12-08 14:30:22
#    📊 Status: SUCCESS
#    📚 Collections: 7
#    💾 Size: 245M
```

## 🔧 Technical Details

### Backup Process
1. **Validation**: Checks Weaviate connectivity and backup module availability
2. **Creation**: Uses Weaviate's filesystem backup API
3. **Verification**: Confirms backup completion and integrity
4. **Cataloging**: Records backup metadata for easy management

### Restore Process
1. **Environment Setup**: Starts fresh Weaviate instance with same configuration
2. **Data Restoration**: Uses Weaviate's restore API to recover all collections
3. **Verification**: Counts documents and collections to ensure completeness
4. **Testing**: Provides tools to verify functionality

### Container Management
- **Project Isolation**: Uses `verba-dr` project name to avoid conflicts
- **Volume Separation**: Fresh `weaviate_dr_data` volume for clean recovery
- **Backup Access**: Mounts same backup directory for access to backup files

## 📊 Expected Results

After successful restore, you should see:
- **178 documents** in VERBA_DOCUMENTS collection
- **51,977+ chunks** in embedding collections
- **7 collections** total (including configuration and suggestions)
- **Functional search** capabilities (BM25, semantic if configured)

## 🚨 Troubleshooting

### Backup Fails
```bash
# Check if Weaviate is running
curl http://localhost:8080/v1/meta

# Check if backup module is enabled
curl -s http://localhost:8080/v1/meta | grep backup-filesystem
```

### Restore Fails
```bash
# Verify backup exists
ls -la ../backups/

# Check disaster recovery container
docker ps | grep weaviate-disaster-recovery

# Check container logs
docker logs weaviate-disaster-recovery
```

### Data Verification Issues
```bash
# Run comprehensive verification
./verify_data.py

# Test sample queries
./query_sample_data.py

# Check Weaviate console
# http://localhost:8080/v1/console
```

## 🔗 Integration with Main Verba

This disaster recovery system is designed to work alongside your main Verba installation:

1. **Backup**: Can be run while Verba is operational
2. **Recovery**: Uses separate container to avoid conflicts
3. **Restoration**: Can restore to either DR environment or main Verba
4. **Verification**: Works with any Weaviate instance

## 📚 Additional Resources

- **Comprehensive Documentation**: `WEAVIATE_BACKUP_DISASTER_RECOVERY.md`
- **Weaviate Backup API**: https://docs.weaviate.io/deploy/configuration/backups
- **Docker Compose Reference**: https://docs.docker.com/compose/

## 🎯 Best Practices

1. **Regular Backups**: Schedule daily backups using cron
2. **Test Restores**: Regularly test disaster recovery procedures
3. **Monitor Space**: Keep an eye on backup directory size
4. **Document Changes**: Update procedures when Verba configuration changes
5. **Secure Backups**: Consider encrypting backups for sensitive data

---

This disaster recovery system provides enterprise-grade backup and restore capabilities for your Verba installation, ensuring your RAG data is always protected and recoverable.
