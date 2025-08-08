#!/usr/bin/env python3
"""
Script to check if documents exist in Weaviate database
This will help us verify if the import actually succeeded despite WebSocket timeout
"""

import asyncio
import weaviate
from weaviate.client import WeaviateAsyncClient
from weaviate.classes.init import AdditionalConfig, Timeout
from wasabi import msg

async def check_weaviate_documents():
    """Check what documents exist in the Weaviate database"""
    
    try:
        # Connect to Weaviate (Docker deployment)
        msg.info("Connecting to Weaviate Docker instance...")
        client = weaviate.use_async_with_local(
            host="weaviate",  # Docker service name
            additional_config=AdditionalConfig(
                timeout=Timeout(init=120, query=600, insert=600)
            ),
        )
        
        async with client:
            msg.info("Connected to Weaviate successfully!")
            
            # Check if VERBA_DOCUMENTS collection exists
            document_collection_name = "VERBA_DOCUMENTS"
            
            if not await client.collections.exists(document_collection_name):
                msg.warn(f"Collection {document_collection_name} does not exist!")
                return
            
            msg.good(f"Collection {document_collection_name} exists!")
            
            # Get the document collection
            document_collection = client.collections.get(document_collection_name)
            
            # Get total count of documents
            response = await document_collection.aggregate.over_all(total_count=True)
            total_count = response.total_count
            
            msg.info(f"Total documents in Weaviate: {total_count}")
            
            if total_count == 0:
                msg.warn("No documents found in Weaviate!")
                return
            
            # Fetch all documents (limit to 10 for display)
            response = await document_collection.query.fetch_objects(
                limit=10,
                return_properties=["title", "extension", "fileSize", "labels", "source"]
            )
            
            msg.info("Documents found in Weaviate:")
            msg.info("=" * 80)
            
            for i, doc in enumerate(response.objects, 1):
                props = doc.properties
                msg.info(f"{i}. Title: {props.get('title', 'N/A')}")
                msg.info(f"   UUID: {doc.uuid}")
                msg.info(f"   Extension: {props.get('extension', 'N/A')}")
                msg.info(f"   File Size: {props.get('fileSize', 'N/A')} bytes")
                msg.info(f"   Labels: {props.get('labels', [])}")
                msg.info(f"   Source: {props.get('source', 'N/A')}")
                msg.info("-" * 40)
            
            # Check specifically for the PDF we were trying to import
            pdf_name = "openedge-developer-studio-help.pdf"
            msg.info(f"\nSearching specifically for '{pdf_name}'...")
            
            # Search for the specific PDF
            search_response = await document_collection.query.bm25(
                query=pdf_name,
                limit=5,
                return_properties=["title", "extension", "fileSize", "labels", "source"]
            )
            
            if len(search_response.objects) > 0:
                msg.good(f"Found {len(search_response.objects)} documents matching '{pdf_name}':")
                for doc in search_response.objects:
                    props = doc.properties
                    msg.info(f"  - {props.get('title', 'N/A')} (UUID: {doc.uuid})")
            else:
                msg.warn(f"No documents found matching '{pdf_name}'")
            
            # Check embedding collections
            msg.info("\nChecking embedding collections...")
            collections = await client.collections.list_all()
            embedding_collections = [col for col in collections if col.startswith("VERBA_Embedding_")]
            
            if embedding_collections:
                msg.info(f"Found {len(embedding_collections)} embedding collections:")
                for col_name in embedding_collections:
                    col = client.collections.get(col_name)
                    response = await col.aggregate.over_all(total_count=True)
                    chunk_count = response.total_count
                    msg.info(f"  - {col_name}: {chunk_count} chunks")
            else:
                msg.warn("No embedding collections found!")
                
    except Exception as e:
        msg.fail(f"Error checking Weaviate: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_weaviate_documents())
