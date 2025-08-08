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
