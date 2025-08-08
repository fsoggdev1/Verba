from fastapi import WebSocket
from goldenverba.server.types import (
    FileStatus,
    StatusReport,
    DataBatchPayload,
    FileConfig,
    CreateNewDocument,
)
from wasabi import msg
import asyncio


class LoggerManager:
    def __init__(self, socket: WebSocket = None):
        self.socket = socket
        self.websocket_failed = False
        self.retry_count = 0
        self.max_retries = 3
        self.error_logged = False  # Track if we've already logged the permanent failure

    async def send_report(
        self, file_Id: str, status: FileStatus, message: str, took: float
    ):
        msg.info(f"{status} | {file_Id} | {message} | {took}")

        # Always continue processing regardless of WebSocket status
        # For critical status updates (SUCCESS/ERROR), reset the failed flag to try again
        if status in [FileStatus.DONE, FileStatus.ERROR]:
            if self.websocket_failed:
                msg.info(f"🔄 Resetting WebSocket failed flag to attempt sending critical {status} status")
                self.websocket_failed = False
                self.error_logged = False

        # Only try WebSocket if it hasn't permanently failed
        if self.socket is not None and not self.websocket_failed:
            await self._try_send_with_retry(file_Id, status, message, took)

    async def _try_send_with_retry(self, file_Id: str, status: str, message: str, took: float):
        """Try to send WebSocket message with retry logic, but don't fail the import if it fails"""
        for attempt in range(self.max_retries):
            try:
                payload: StatusReport = {
                    "fileID": file_Id,
                    "status": status,
                    "message": message,
                    "took": took,
                }

                # Always try to send, even if connection state is questionable
                # The send operation itself will fail if the connection is truly dead
                await self.socket.send_json(payload)
                msg.info(f"✅ Successfully sent {status} status for {file_Id}")
                return  # Success, exit retry loop

            except Exception as e:
                # Check for specific WebSocket state errors
                error_str = str(e).lower()
                if any(phrase in error_str for phrase in [
                    "need to call \"accept\" first",
                    "websocket is not connected",
                    "cannot call \"send\" once a close message has been sent",
                    "websocket connection is closed",
                    "connection is closed"
                ]):
                    # These are permanent WebSocket state errors - don't retry
                    self.websocket_failed = True
                    if not self.error_logged:
                        msg.warn(f"🔌 WebSocket connection permanently failed: {str(e)}")
                        self.error_logged = True
                    return

                # For other errors, retry
                if attempt == 0:
                    msg.warn(f"🔄 WebSocket send failed, attempting {self.max_retries} retries: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5)  # Brief pause before retry
                else:
                    self.websocket_failed = True
                    if not self.error_logged:
                        msg.warn(f"❌ WebSocket permanently failed after {self.max_retries} attempts, continuing without status updates")
                        self.error_logged = True
                    return

    def _is_websocket_connected(self) -> bool:
        """Check if WebSocket is in a valid connected state"""
        if self.socket is None:
            return False

        try:
            # For FastAPI WebSocket, try to check the connection state
            # If the WebSocket has been closed or is in an invalid state, this will fail
            from starlette.websockets import WebSocketState

            # Check if the WebSocket has the client_state attribute and it's connected
            if hasattr(self.socket, 'client_state'):
                return self.socket.client_state == WebSocketState.CONNECTED

            # Fallback: assume connected if we can't check the state
            # The actual send operation will fail if it's not connected
            return True

        except Exception:
            # If we can't check the state, assume it's not connected
            return False

    async def send_heartbeat(self, file_Id: str, message: str = "Processing..."):
        """Send simple heartbeat - but don't fail if WebSocket is down"""
        if self.socket is not None and not self.websocket_failed and self._is_websocket_connected():
            try:
                payload: StatusReport = {
                    "fileID": file_Id,
                    "status": "PROCESSING",
                    "message": message,
                    "took": 0,
                }
                await self.socket.send_json(payload)
            except Exception as e:
                # Don't log every heartbeat failure, just mark as failed
                self.websocket_failed = True

    async def create_new_document(
        self, new_file_id: str, document_name: str, original_file_id: str
    ):
        msg.info(f"Creating new file {new_file_id} from {original_file_id}")
        if self.socket is not None and not self.websocket_failed:
            try:
                payload: CreateNewDocument = {
                    "new_file_id": new_file_id,
                    "filename": document_name,
                    "original_file_id": original_file_id,
                }
                await self.socket.send_json(payload)
            except Exception as e:
                self.websocket_failed = True
                if not self.error_logged:
                    msg.warn(f"Failed to create new document notification: {str(e)} - continuing anyway")
                    self.error_logged = True


class BatchManager:
    def __init__(self):
        self.batches = {}

    def add_batch(self, payload: DataBatchPayload) -> FileConfig:
        try:
            # Removed verbose batch logging to reduce debug message spam

            if payload.fileID not in self.batches:
                self.batches[payload.fileID] = {
                    "fileID": payload.fileID,
                    "total": payload.total,
                    "chunks": {},
                }

            self.batches[payload.fileID]["chunks"][payload.order] = payload.chunk

            fileConfig = self.check_batch(payload.fileID)

            if fileConfig is not None or payload.isLastChunk:
                msg.info(f"Removing {payload.fileID} from BatchManager")
                del self.batches[payload.fileID]

            return fileConfig

        except Exception as e:
            msg.fail(f"Failed to add batch to BatchManager: {str(e)}")

    def check_batch(self, fileID: str):
        if len(self.batches[fileID]["chunks"].keys()) == self.batches[fileID]["total"]:
            msg.good(f"Collected all Batches of {fileID}")
            chunks = self.batches[fileID]["chunks"]
            data = "".join([chunks[chunk] for chunk in chunks])
            return FileConfig.model_validate_json(data)
        else:
            return None
