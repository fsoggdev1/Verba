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
