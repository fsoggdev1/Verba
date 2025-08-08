from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
import asyncio

from goldenverba.server.helpers import LoggerManager, BatchManager
from weaviate.client import WeaviateAsyncClient
from weaviate.classes.query import Filter
from pydantic import BaseModel

import os
from pathlib import Path

from dotenv import load_dotenv
from starlette.websockets import WebSocketDisconnect
from wasabi import msg  # type: ignore[import]

from goldenverba import verba_manager

from goldenverba.server.types import (
    ResetPayload,
    QueryPayload,
    GeneratePayload,
    Credentials,
    GetDocumentPayload,
    ConnectPayload,
    DatacountPayload,
    GetSuggestionsPayload,
    GetAllSuggestionsPayload,
    DeleteSuggestionPayload,
    GetContentPayload,
    SetThemeConfigPayload,
    SetUserConfigPayload,
    SearchQueryPayload,
    SetRAGConfigPayload,
    GetChunkPayload,
    GetVectorPayload,
    DataBatchPayload,
    ChunksPayload,
    FileConfig,
    FileStatus,
)

load_dotenv()

# Check if runs in production
production_key = os.environ.get("VERBA_PRODUCTION")
tag = os.environ.get("VERBA_GOOGLE_TAG", "")


if production_key:
    msg.info(f"Verba runs in {production_key} mode")
    production = production_key
else:
    production = "Local"

manager = verba_manager.VerbaManager()

client_manager = verba_manager.ClientManager()

### Lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await client_manager.disconnect()


# FastAPI App
app = FastAPI(lifespan=lifespan)

# Allow requests only from the same origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # This will be restricted by the custom middleware
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom middleware to check if the request is from the same origin
@app.middleware("http")
async def check_same_origin(request: Request, call_next):
    # Allow public access to /api/health
    if request.url.path == "/api/health":
        return await call_next(request)

    origin = request.headers.get("origin")
    if origin == str(request.base_url).rstrip("/") or (
        origin
        and origin.startswith("http://localhost:")
        and request.base_url.hostname == "localhost"
    ):
        return await call_next(request)
    else:
        # Only apply restrictions to /api/ routes (except /api/health)
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Not allowed",
                    "details": {
                        "request_origin": origin,
                        "expected_origin": str(request.base_url),
                        "request_method": request.method,
                        "request_url": str(request.url),
                        "request_headers": dict(request.headers),
                        "expected_header": "Origin header matching the server's base URL or localhost",
                    },
                },
            )

        # Allow non-API routes to pass through
        return await call_next(request)


BASE_DIR = Path(__file__).resolve().parent

# Serve the assets (JS, CSS, images, etc.)
app.mount(
    "/static/_next",
    StaticFiles(directory=BASE_DIR / "frontend/out/_next"),
    name="next-assets",
)

# Serve the main page and other static files
app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend/out"), name="app")


@app.get("/")
@app.head("/")
async def serve_frontend():
    return FileResponse(os.path.join(BASE_DIR, "frontend/out/index.html"))


### INITIAL ENDPOINTS


# Define health check endpoint
@app.get("/api/health")
async def health_check():

    await client_manager.clean_up()

    if production == "Local":
        deployments = await manager.get_deployments()
    else:
        deployments = {"WEAVIATE_URL_VERBA": "", "WEAVIATE_API_KEY_VERBA": ""}

    return JSONResponse(
        content={
            "message": "Alive!",
            "production": production,
            "gtag": tag,
            "deployments": deployments,
            "default_deployment": os.getenv("DEFAULT_DEPLOYMENT", ""),
        }
    )


@app.post("/api/connect")
async def connect_to_verba(payload: ConnectPayload):
    try:
        client = await client_manager.connect(payload.credentials, payload.port)
        if isinstance(
            client, WeaviateAsyncClient
        ):  # Check if client is an AsyncClient object
            config = await manager.load_rag_config(client)
            user_config = await manager.load_user_config(client)
            theme, themes = await manager.load_theme_config(client)
            return JSONResponse(
                status_code=200,
                content={
                    "connected": True,
                    "error": "",
                    "rag_config": config,
                    "user_config": user_config,
                    "theme": theme,
                    "themes": themes,
                },
            )
        else:
            raise TypeError(
                "Couldn't connect to Weaviate, client is not an AsyncClient object"
            )
    except Exception as e:
        msg.fail(f"Failed to connect to Weaviate {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "connected": False,
                "error": f"Failed to connect to Weaviate {str(e)}",
                "rag_config": {},
                "theme": {},
                "themes": {},
            },
        )


### WEBSOCKETS

async def check_document_in_weaviate_with_retry(client, fileConfig: FileConfig, max_retries: int = 3) -> bool:
    """
    Check if a document was successfully imported to Weaviate with retry logic.
    Returns True if document exists, False otherwise.
    """
    for attempt in range(max_retries):
        try:
            # Check if the document collection exists
            document_collection_name = "VERBA_DOCUMENTS"
            if not await client.collections.exists(document_collection_name):
                if attempt == 0:  # Only log on first attempt
                    msg.warn(f"❌ Document collection {document_collection_name} does not exist")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # Wait 1 second before retry
                    continue
                return False

            # Get the document collection and search for the file
            document_collection = client.collections.get(document_collection_name)

            # Search for documents with matching title using BM25 with timeout protection
            try:
                # Add timeout to prevent infinite loops in BM25 search
                response = await asyncio.wait_for(
                    document_collection.query.bm25(
                        query=fileConfig.filename,
                        limit=5,
                        return_properties=["title", "extension", "fileSize"]
                    ),
                    timeout=30.0  # 30 second timeout for BM25 search
                )

                if response.objects and len(response.objects) > 0:
                    # Check if any document has an exact title match
                    for doc in response.objects:
                        if doc.properties.get("title") == fileConfig.filename:
                            msg.info(f"✅ Document {fileConfig.filename} found in Weaviate (UUID: {doc.uuid})")
                            return True

                    if attempt == 0:  # Only log on first attempt
                        msg.warn(f"❌ No exact match for {fileConfig.filename} (found {len(response.objects)} similar documents)")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)  # Wait 2 seconds before retry
                        continue
                    return False

                if attempt == 0:  # Only log on first attempt
                    msg.warn(f"❌ Document {fileConfig.filename} not found in Weaviate")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Wait 2 seconds before retry
                    continue
                return False

            except asyncio.TimeoutError:
                if attempt == 0:  # Only log on first attempt
                    msg.warn(f"⏰ BM25 search timed out after 30 seconds for {fileConfig.filename}")
                    msg.info("🔄 Falling back to property filter for exact match...")

                # Fallback to property filter if BM25 times out
                from weaviate.classes.query import Filter
                fallback_response = await document_collection.query.fetch_objects(
                    filters=Filter.by_property("title").equal(fileConfig.filename),
                    limit=1,
                    return_properties=["title", "extension", "fileSize"]
                )

                if fallback_response.objects and len(fallback_response.objects) > 0:
                    doc = fallback_response.objects[0]
                    msg.info(f"✅ Document {fileConfig.filename} found via fallback (UUID: {doc.uuid})")
                    return True
                else:
                    if attempt == 0:  # Only log on first attempt
                        msg.warn(f"❌ Document {fileConfig.filename} not found via fallback either")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)  # Wait 2 seconds before retry
                        continue
                    return False

        except Exception as e:
            if attempt == 0:  # Only log on first attempt
                msg.warn(f"⚠️ Error checking document in Weaviate: {str(e)}")
                msg.info(f"🔍 Attempted to verify document: {fileConfig.filename}")
            if attempt < max_retries - 1:
                msg.warn(f"🔄 Retrying document verification (attempt {attempt + 2}/{max_retries})...")
                await asyncio.sleep(2)  # Wait 2 seconds before retry
                continue
            else:
                msg.warn(f"❌ Document verification failed after {max_retries} attempts")
                return False

    return False


# Keep the old function name for backward compatibility
async def check_document_in_weaviate(client, fileConfig: FileConfig) -> bool:
    """Backward compatibility wrapper"""
    return await check_document_in_weaviate_with_retry(client, fileConfig, max_retries=3)


async def resilient_import_document(client, fileConfig: FileConfig, logger: LoggerManager, credentials=None):
    """
    Import document with resilience to WebSocket failures.
    This function continues processing even if WebSocket connection dies,
    and verifies the actual import result by checking Weaviate.
    """
    import time
    start_time = time.time()

    msg.info(f"🚀 RESILIENT IMPORT STARTED for {fileConfig.filename}")
    msg.info(f"📊 Expected processing time: ~15-20 minutes")

    # Store credentials for reconnection purposes (don't modify fileConfig)
    stored_credentials = credentials

    import_error = None

    try:
        # Call the actual import function with credentials for reconnection
        await manager.import_document(client, fileConfig, logger, stored_credentials)
        msg.good(f"✅ Import function completed for {fileConfig.filename}")

    except Exception as e:
        import_error = e
        msg.warn(f"⚠️ Import function failed for {fileConfig.filename}: {str(e)}")

    # Always check if the document actually made it to Weaviate
    total_time = time.time() - start_time
    msg.info(f"🔍 Checking if {fileConfig.filename} was successfully imported to Weaviate...")

    # Small delay to ensure document is fully committed to Weaviate
    await asyncio.sleep(2)

    # Create a fresh client connection for verification to avoid using a potentially closed client
    verification_client = None
    document_exists = False
    try:
        if stored_credentials:
            from goldenverba.server.api import client_manager
            verification_client = await client_manager.connect(stored_credentials)
            document_exists = await check_document_in_weaviate_with_retry(verification_client, fileConfig, max_retries=3)
        else:
            # Fallback to existing client if no credentials available
            document_exists = await check_document_in_weaviate_with_retry(client, fileConfig, max_retries=3)
    except Exception as verification_error:
        msg.warn(f"⚠️ Verification failed with error: {str(verification_error)}, trying with existing client...")
        try:
            # Fallback to existing client with retry
            document_exists = await check_document_in_weaviate_with_retry(client, fileConfig, max_retries=3)
        except Exception as fallback_error:
            msg.warn(f"⚠️ Both verification attempts failed after retries: {str(fallback_error)}")
            document_exists = False

    if document_exists:
        # Document successfully imported, send success status
        msg.good(f"🎉 Document {fileConfig.filename} successfully imported to Weaviate in {total_time:.1f}s")
        try:
            await logger.send_report(
                fileConfig.fileID,
                status=FileStatus.DONE,
                message=f"Import for {fileConfig.filename} completed successfully",
                took=total_time,
            )
            # Success report sent (removed verbose logging)
        except Exception as report_error:
            msg.warn(f"📤 Could not send success report via WebSocket: {str(report_error)} - but import succeeded")
    else:
        # Document not found in Weaviate, send error status
        if import_error:
            error_message = f"Import failed: {str(import_error)}"
            msg.fail(f"💥 Import failed for {fileConfig.filename}: {error_message}")
        else:
            error_message = f"Document not found in Weaviate after import (verification failed)"
            msg.warn(f"⚠️ Verification failed for {fileConfig.filename}: {error_message}")
            msg.info(f"💡 Note: Document may still be successfully imported - check Weaviate directly")

        try:
            await logger.send_report(
                fileConfig.fileID,
                status=FileStatus.ERROR,
                message=error_message,
                took=total_time,
            )
            # Error report sent (removed verbose logging)
        except Exception as report_error:
            msg.warn(f"📤 Could not send error report via WebSocket: {str(report_error)} - but import failure is logged")

        # Raise the original error if there was one, or a new error if document not found
        if import_error:
            raise import_error
        else:
            raise Exception("Document not found in Weaviate after import")


@app.websocket("/ws/generate_stream")
async def websocket_generate_stream(websocket: WebSocket):
    await websocket.accept()
    while True:  # Start a loop to keep the connection alive.
        try:
            data = await websocket.receive_text()
            # Parse and validate the JSON string using Pydantic model
            payload = GeneratePayload.model_validate_json(data)

            msg.good(f"Received generate stream call for {payload.query}")

            full_text = ""
            async for chunk in manager.generate_stream_answer(
                payload.rag_config,
                payload.query,
                payload.context,
                payload.conversation,
            ):
                full_text += chunk["message"]
                if chunk["finish_reason"] == "stop":
                    chunk["full_text"] = full_text
                await websocket.send_json(chunk)

        except WebSocketDisconnect:
            msg.warn("WebSocket connection closed by client.")
            break  # Break out of the loop when the client disconnects

        except Exception as e:
            msg.fail(f"WebSocket Error: {str(e)}")
            await websocket.send_json(
                {"message": e, "finish_reason": "stop", "full_text": str(e)}
            )
        msg.good("Succesfully streamed answer")


@app.websocket("/ws/import_files")
async def websocket_import_files(websocket: WebSocket):

    if production == "Demo":
        return

    try:
        await websocket.accept()
        msg.info("🔌 WebSocket connection accepted for import")
        logger = LoggerManager(websocket)
        batcher = BatchManager()
    except Exception as e:
        msg.warn(f"⚠️ Failed to accept WebSocket connection: {str(e)}")
        return

    # Note: Removed WebSocket heartbeat ping as it's not needed with retry logic in place
    # The LoggerManager already handles WebSocket failures with 3 retries

    try:
        while True:
            try:
                data = await websocket.receive_text()
                batch_data = DataBatchPayload.model_validate_json(data)
                fileConfig = batcher.add_batch(batch_data)

                # Only log when we get the complete fileConfig, not every batch
                if fileConfig is not None:
                    msg.info(f"🔥 ALL BATCHES COLLECTED for {fileConfig.filename} - Starting resilient import")

                if fileConfig is not None:
                    client = await client_manager.connect(batch_data.credentials)

                    # Call resilient import function
                    try:
                        msg.info(f"🚀 CALLING RESILIENT IMPORT for {fileConfig.filename}")
                        await resilient_import_document(client, fileConfig, logger, batch_data.credentials)
                        msg.good(f"🎉 RESILIENT IMPORT COMPLETED SUCCESSFULLY for {fileConfig.filename}")
                    except Exception as e:
                        msg.fail(f"💥 RESILIENT IMPORT FAILED for {fileConfig.filename}: {str(e)}")

                        # Send error report but don't break the WebSocket loop
                        try:
                            await logger.send_report(
                                fileConfig.fileID,
                                status=FileStatus.ERROR,
                                message=f"Resilient import failed: {str(e)}",
                                took=0,
                            )
                        except Exception as report_error:
                            msg.warn(f"Could not send error report: {str(report_error)}")

            except WebSocketDisconnect:
                msg.warn("🔌 Import WebSocket connection closed by client - but background imports will continue")
                break
            except Exception as e:
                error_str = str(e).lower()
                # Check for WebSocket connection state errors
                if any(phrase in error_str for phrase in [
                    "need to call \"accept\" first",
                    "websocket is not connected",
                    "cannot call \"send\" once a close message has been sent",
                    "websocket connection is closed"
                ]):
                    msg.warn(f"🔌 WebSocket connection error: {str(e)} - background imports will continue")
                    msg.info("📋 Check console logs for import progress")
                    break
                else:
                    msg.warn(f"⚠️ Import WebSocket Error: {str(e)}")
                    # For other errors, continue processing
                    continue

    finally:
        # Note: No heartbeat task to cancel since we removed the ping functionality

        # Log background tasks status but DON'T cancel them
        if hasattr(websocket, '_background_tasks'):
            active_tasks = [task for task in websocket._background_tasks if not task.done()]
            if active_tasks:
                msg.info(f"🔄 {len(active_tasks)} background import tasks will continue running after WebSocket closes")
                # Background tasks continuing (removed verbose per-task logging)
            else:
                msg.info("✅ All background import tasks completed")

        # WebSocket handler cleanup completed (removed verbose logging)


### CONFIG ENDPOINTS


# Get Configuration
@app.post("/api/get_rag_config")
async def retrieve_rag_config(payload: Credentials):
    try:
        client = await client_manager.connect(payload)
        config = await manager.load_rag_config(client)
        return JSONResponse(
            status_code=200, content={"rag_config": config, "error": ""}
        )

    except Exception as e:
        msg.warn(f"Could not retrieve configuration: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "rag_config": {},
                "error": f"Could not retrieve rag configuration: {str(e)}",
            },
        )


@app.post("/api/set_rag_config")
async def update_rag_config(payload: SetRAGConfigPayload):
    if production == "Demo":
        return JSONResponse(
            content={
                "status": "200",
                "status_msg": "Config can't be updated in Production Mode",
            }
        )

    try:
        client = await client_manager.connect(payload.credentials)
        await manager.set_rag_config(client, payload.rag_config.model_dump())
        return JSONResponse(
            content={
                "status": 200,
            }
        )
    except Exception as e:
        msg.warn(f"Failed to set new RAG Config {str(e)}")
        return JSONResponse(
            content={
                "status": 400,
                "status_msg": f"Failed to set new RAG Config {str(e)}",
            }
        )


@app.post("/api/get_user_config")
async def retrieve_user_config(payload: Credentials):
    try:
        client = await client_manager.connect(payload)
        config = await manager.load_user_config(client)
        return JSONResponse(
            status_code=200, content={"user_config": config, "error": ""}
        )

    except Exception as e:
        msg.warn(f"Could not retrieve user configuration: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "user_config": {},
                "error": f"Could not retrieve rag configuration: {str(e)}",
            },
        )


@app.post("/api/set_user_config")
async def update_user_config(payload: SetUserConfigPayload):
    if production == "Demo":
        return JSONResponse(
            content={
                "status": "200",
                "status_msg": "Config can't be updated in Production Mode",
            }
        )

    try:
        client = await client_manager.connect(payload.credentials)
        await manager.set_user_config(client, payload.user_config)
        return JSONResponse(
            content={
                "status": 200,
                "status_msg": "User config updated",
            }
        )
    except Exception as e:
        msg.warn(f"Failed to set new RAG Config {str(e)}")
        return JSONResponse(
            content={
                "status": 400,
                "status_msg": f"Failed to set new RAG Config {str(e)}",
            }
        )


# Get Configuration
@app.post("/api/get_theme_config")
async def retrieve_theme_config(payload: Credentials):
    try:
        client = await client_manager.connect(payload)
        theme, themes = await manager.load_theme_config(client)
        return JSONResponse(
            status_code=200, content={"theme": theme, "themes": themes, "error": ""}
        )

    except Exception as e:
        msg.warn(f"Could not retrieve configuration: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "theme": None,
                "themes": None,
                "error": f"Could not retrieve theme configuration: {str(e)}",
            },
        )


@app.post("/api/set_theme_config")
async def update_theme_config(payload: SetThemeConfigPayload):
    if production == "Demo":
        return JSONResponse(
            content={
                "status": "200",
                "status_msg": "Config can't be updated in Production Mode",
            }
        )

    try:
        client = await client_manager.connect(payload.credentials)
        await manager.set_theme_config(
            client, {"theme": payload.theme, "themes": payload.themes}
        )
        return JSONResponse(
            content={
                "status": 200,
            }
        )
    except Exception as e:
        msg.warn(f"Failed to set new RAG Config {str(e)}")
        return JSONResponse(
            content={
                "status": 400,
                "status_msg": f"Failed to set new RAG Config {str(e)}",
            }
        )


### RAG ENDPOINTS


# Receive query and return chunks and query answer
@app.post("/api/query")
async def query(payload: QueryPayload):
    msg.good(f"Received query: {payload.query}")
    try:
        client = await client_manager.connect(payload.credentials)
        documents_uuid = [document.uuid for document in payload.documentFilter]
        documents, context = await manager.retrieve_chunks(
            client, payload.query, payload.RAG, payload.labels, documents_uuid
        )

        return JSONResponse(
            content={"error": "", "documents": documents, "context": context}
        )
    except Exception as e:
        msg.warn(f"Query failed: {str(e)}")
        return JSONResponse(
            content={"error": f"Query failed: {str(e)}", "documents": [], "context": ""}
        )


### DOCUMENT ENDPOINTS


# Retrieve specific document based on UUID
@app.post("/api/get_document")
async def get_document(payload: GetDocumentPayload):
    try:
        client = await client_manager.connect(payload.credentials)
        document = await manager.weaviate_manager.get_document(
            client,
            payload.uuid,
            properties=[
                "title",
                "extension",
                "fileSize",
                "labels",
                "source",
                "meta",
                "metadata",
            ],
        )
        if document is not None:
            document["content"] = ""
            msg.good(f"Succesfully retrieved document: {document['title']}")
            return JSONResponse(
                content={
                    "error": "",
                    "document": document,
                }
            )
        else:
            msg.warn(f"Could't retrieve document")
            return JSONResponse(
                content={
                    "error": "Couldn't retrieve requested document",
                    "document": None,
                }
            )
    except Exception as e:
        msg.fail(f"Document retrieval failed: {str(e)}")
        return JSONResponse(
            content={
                "error": str(e),
                "document": None,
            }
        )


@app.post("/api/get_datacount")
async def get_document_count(payload: DatacountPayload):
    try:
        client = await client_manager.connect(payload.credentials)
        document_uuids = [document.uuid for document in payload.documentFilter]
        datacount = await manager.weaviate_manager.get_datacount(
            client, payload.embedding_model, document_uuids
        )
        return JSONResponse(
            content={
                "datacount": datacount,
            }
        )
    except Exception as e:
        msg.fail(f"Document Count retrieval failed: {str(e)}")
        return JSONResponse(
            content={
                "datacount": 0,
            }
        )


@app.post("/api/get_labels")
async def get_labels(payload: Credentials):
    try:
        client = await client_manager.connect(payload)
        labels = await manager.weaviate_manager.get_labels(client)
        return JSONResponse(
            content={
                "labels": labels,
            }
        )
    except Exception as e:
        msg.fail(f"Document Labels retrieval failed: {str(e)}")
        return JSONResponse(
            content={
                "labels": [],
            }
        )


# Retrieve specific document based on UUID
@app.post("/api/get_content")
async def get_content(payload: GetContentPayload):
    try:
        client = await client_manager.connect(payload.credentials)
        content, maxPage = await manager.get_content(
            client, payload.uuid, payload.page - 1, payload.chunkScores
        )
        msg.good(f"Succesfully retrieved content from {payload.uuid}")
        return JSONResponse(
            content={"error": "", "content": content, "maxPage": maxPage}
        )
    except Exception as e:
        msg.fail(f"Document retrieval failed: {str(e)}")
        return JSONResponse(
            content={
                "error": str(e),
                "document": None,
            }
        )


# Retrieve specific document based on UUID
@app.post("/api/get_vectors")
async def get_vectors(payload: GetVectorPayload):
    try:
        client = await client_manager.connect(payload.credentials)
        vector_groups = await manager.weaviate_manager.get_vectors(
            client, payload.uuid, payload.showAll
        )
        return JSONResponse(
            content={
                "error": "",
                "vector_groups": vector_groups,
            }
        )
    except Exception as e:
        msg.fail(f"Vector retrieval failed: {str(e)}")
        return JSONResponse(
            content={
                "error": str(e),
                "payload": {"embedder": "None", "vectors": []},
            }
        )


# Retrieve specific document based on UUID
@app.post("/api/get_chunks")
async def get_chunks(payload: ChunksPayload):
    try:
        client = await client_manager.connect(payload.credentials)
        chunks = await manager.weaviate_manager.get_chunks(
            client, payload.uuid, payload.page, payload.pageSize
        )
        return JSONResponse(
            content={
                "error": "",
                "chunks": chunks,
            }
        )
    except Exception as e:
        msg.fail(f"Chunk retrieval failed: {str(e)}")
        return JSONResponse(
            content={
                "error": str(e),
                "chunks": None,
            }
        )


# Retrieve specific document based on UUID
@app.post("/api/get_chunk")
async def get_chunk(payload: GetChunkPayload):
    try:
        client = await client_manager.connect(payload.credentials)
        chunk = await manager.weaviate_manager.get_chunk(
            client, payload.uuid, payload.embedder
        )
        return JSONResponse(
            content={
                "error": "",
                "chunk": chunk,
            }
        )
    except Exception as e:
        msg.fail(f"Chunk retrieval failed: {str(e)}")
        return JSONResponse(
            content={
                "error": str(e),
                "chunk": None,
            }
        )


## Retrieve and search documents imported to Weaviate
@app.post("/api/get_all_documents")
async def get_all_documents(payload: SearchQueryPayload):
    try:
        client = await client_manager.connect(payload.credentials)
        documents, total_count = await manager.weaviate_manager.get_documents(
            client,
            payload.query,
            payload.pageSize,
            payload.page,
            payload.labels,
            properties=["title", "extension", "fileSize", "labels", "source", "meta"],
        )
        labels = await manager.weaviate_manager.get_labels(client)

        msg.good(f"Succesfully retrieved document: {len(documents)} documents")
        return JSONResponse(
            content={
                "documents": documents,
                "labels": labels,
                "error": "",
                "totalDocuments": total_count,
            }
        )
    except Exception as e:
        msg.fail(f"Retrieving all documents failed: {str(e)}")
        return JSONResponse(
            content={
                "documents": [],
                "label": [],
                "error": f"All Document retrieval failed: {str(e)}",
                "totalDocuments": 0,
            }
        )


# Delete specific document based on UUID
@app.post("/api/delete_document")
async def delete_document(payload: GetDocumentPayload):
    if production == "Demo":
        msg.warn("Can't delete documents when in Production Mode")
        return JSONResponse(status_code=200, content={})

    try:
        client = await client_manager.connect(payload.credentials)
        msg.info(f"Deleting {payload.uuid}")
        await manager.weaviate_manager.delete_document(client, payload.uuid)
        return JSONResponse(status_code=200, content={})

    except Exception as e:
        msg.fail(f"Deleting Document with ID {payload.uuid} failed: {str(e)}")
        return JSONResponse(status_code=400, content={})


### ADMIN


@app.post("/api/reset")
async def reset_verba(payload: ResetPayload):
    if production == "Demo":
        return JSONResponse(status_code=200, content={})

    try:
        client = await client_manager.connect(payload.credentials)
        if payload.resetMode == "ALL":
            await manager.weaviate_manager.delete_all(client)
        elif payload.resetMode == "DOCUMENTS":
            await manager.weaviate_manager.delete_all_documents(client)
        elif payload.resetMode == "CONFIG":
            await manager.weaviate_manager.delete_all_configs(client)
        elif payload.resetMode == "SUGGESTIONS":
            await manager.weaviate_manager.delete_all_suggestions(client)

        msg.info(f"Resetting Verba in ({payload.resetMode}) mode")

        return JSONResponse(status_code=200, content={})

    except Exception as e:
        msg.warn(f"Failed to reset Verba {str(e)}")
        return JSONResponse(status_code=500, content={})


# Get Status meta data
@app.post("/api/get_meta")
async def get_meta(payload: Credentials):
    try:
        client = await client_manager.connect(payload)
        node_payload, collection_payload = await manager.weaviate_manager.get_metadata(
            client
        )
        return JSONResponse(
            content={
                "error": "",
                "node_payload": node_payload,
                "collection_payload": collection_payload,
            }
        )
    except Exception as e:
        return JSONResponse(
            content={
                "error": f"Couldn't retrieve metadata {str(e)}",
                "node_payload": {},
                "collection_payload": {},
            }
        )


### Suggestions


@app.post("/api/get_suggestions")
async def get_suggestions(payload: GetSuggestionsPayload):
    try:
        client = await client_manager.connect(payload.credentials)
        suggestions = await manager.weaviate_manager.retrieve_suggestions(
            client, payload.query, payload.limit
        )
        return JSONResponse(
            content={
                "suggestions": suggestions,
            }
        )
    except Exception:
        return JSONResponse(
            content={
                "suggestions": [],
            }
        )


@app.post("/api/get_all_suggestions")
async def get_all_suggestions(payload: GetAllSuggestionsPayload):
    try:
        client = await client_manager.connect(payload.credentials)
        suggestions, total_count = (
            await manager.weaviate_manager.retrieve_all_suggestions(
                client, payload.page, payload.pageSize
            )
        )
        return JSONResponse(
            content={
                "suggestions": suggestions,
                "total_count": total_count,
            }
        )
    except Exception:
        return JSONResponse(
            content={
                "suggestions": [],
                "total_count": 0,
            }
        )


@app.post("/api/delete_suggestion")
async def delete_suggestion(payload: DeleteSuggestionPayload):
    try:
        client = await client_manager.connect(payload.credentials)
        await manager.weaviate_manager.delete_suggestions(client, payload.uuid)
        return JSONResponse(
            content={
                "status": 200,
            }
        )
    except Exception:
        return JSONResponse(
            content={
                "status": 400,
            }
        )


class CheckDocumentStatusPayload(BaseModel):
    filename: str
    credentials: Credentials


@app.post("/api/check_document_status")
async def check_document_status(payload: CheckDocumentStatusPayload):
    """Check if a document exists in Weaviate by filename"""
    try:
        msg.info(f"🔍 Received payload: filename={payload.filename}, credentials type={type(payload.credentials)}")
        msg.info(f"🔍 Credentials: {payload.credentials}")

        client = await client_manager.connect(payload.credentials)

        # Query Weaviate to check if document exists
        document_collection = client.collections.get("VERBA_DOCUMENTS")

        # Use exact case-insensitive match with proper Weaviate filter
        # First try with exact case-sensitive match
        response = await document_collection.query.fetch_objects(
            limit=1,
            return_properties=["title", "extension", "fileSize"],
            filters=Filter.by_property("title").equal(payload.filename)
        )

        # If no exact match, try case-insensitive by fetching all and filtering
        if len(response.objects) == 0:
            msg.info(f"🔍 No exact case-sensitive match for '{payload.filename}', trying case-insensitive")

            # Fetch all documents and do case-insensitive comparison
            all_docs_response = await document_collection.query.fetch_objects(
                limit=1000,
                return_properties=["title", "extension", "fileSize"]
            )

            target_filename_lower = payload.filename.lower()
            exact_matches = []

            for obj in all_docs_response.objects:
                stored_title = obj.properties.get('title', '')
                if stored_title.lower() == target_filename_lower:
                    exact_matches.append(obj)
                    msg.info(f"🔍 Case-insensitive match found: '{stored_title}' matches '{payload.filename}'")

            exists = len(exact_matches) > 0
        else:
            exists = True
            msg.info(f"🔍 Exact case-sensitive match found for '{payload.filename}'")

        msg.info(f"📋 Document status check for '{payload.filename}': {'EXISTS' if exists else 'NOT FOUND'}")
        return {"exists": exists}

    except Exception as e:
        msg.warn(f"Failed to check document status for {payload.filename}: {str(e)}")
        return {"exists": False, "error": str(e)}



