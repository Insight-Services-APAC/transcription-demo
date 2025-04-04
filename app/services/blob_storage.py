import os
import time
from azure.storage.blob import (
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
    BlobSasPermissions,
)
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import threading
import json
from urllib.parse import urlparse
import logging
from app.errors.exceptions import StorageError, ValidationError
from app.errors.service_helper import retry_on_error, log_service_call, ServiceBase

logger = logging.getLogger(__name__)


class BlobStorageService(ServiceBase):

    def __init__(self, connection_string, container_name):
        """
        Initialize BlobStorageService with an Azure Storage connection string
        and container name. We'll generate SAS URLs after we upload files.
        """
        super().__init__(service_name="BlobStorage")
        if not connection_string:
            raise ValidationError(
                "Azure Storage connection string is required", field="connection_string"
            )
        if not container_name:
            raise ValidationError(
                "Azure Storage container name is required", field="container_name"
            )
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                connection_string
            )
            self.container_name = container_name
            self.upload_progress = {}
            self.upload_lock = threading.Lock()
            logger.info(
                f"BlobStorageService initialized (thread ID: {threading.get_ident()})"
            )
            try:
                self.blob_service_client.create_container(self.container_name)
            except Exception:
                pass
        except Exception as e:
            raise StorageError(
                f"Failed to initialize Azure Blob Storage client: {str(e)}",
                container=container_name,
            )

    @log_service_call("BlobStorage")
    @retry_on_error(max_retries=3, retry_delay=2, exceptions=(Exception,))
    def upload_file(self, file_path, blob_path, upload_id=None, progress_tracker=None):
        """
        Upload a file from local path to Azure Blob Storage and then
        generate a read-only SAS URL that the Speech API can use.

        Args:
            file_path (str): path to local file
            blob_path (str): desired path/name in blob storage
            upload_id (str, optional): ID for tracking progress
            progress_tracker: UploadProgressTracker instance for Redis-based progress tracking

        Returns:
            str: A SAS URL for the uploaded blob (with read permission).
        """
        if not file_path:
            raise ValidationError("File path is required", field="file_path")
        if not blob_path:
            raise ValidationError("Blob path is required", field="blob_path")
        if not os.path.exists(file_path):
            raise StorageError(f"Local file not found: {file_path}", filename=file_path)
        sas_url = None
        logger.info(
            f"Starting upload_file: file_path={file_path}, blob_path={blob_path}, upload_id={upload_id}"
        )
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=blob_path
            )
        except Exception as e:
            raise StorageError(
                f"Failed to create blob client: {str(e)}",
                container=self.container_name,
                blob_path=blob_path,
            )
        content_type = self._get_content_type(file_path)
        file_size = os.path.getsize(file_path)
        logger.info(
            f"Uploading file of size {file_size} bytes with content-type={content_type}"
        )
        uploaded_bytes = 0
        callback_count = 0

        def progress_callback(current):
            nonlocal uploaded_bytes, callback_count
            callback_count += 1
            if hasattr(current, "context") and hasattr(current.context, "data_read"):
                current = getattr(current.context, "data_read", 1024)
            elif not isinstance(current, (int, float)):
                current = 1024
            uploaded_bytes += current
            if upload_id:
                if progress_tracker:
                    progress_data = {
                        "status": "uploading",
                        "progress": min(99, int(uploaded_bytes / file_size * 100)),
                        "file_size": file_size,
                        "uploaded_bytes": uploaded_bytes,
                        "stage": "azure_upload",
                        "azure_status": "in_progress",
                    }
                    progress_tracker.update_progress(upload_id, progress_data)
                else:
                    with self.upload_lock:
                        if upload_id not in self.upload_progress:
                            self.upload_progress[upload_id] = {
                                "status": "uploading",
                                "progress": 0,
                                "file_size": file_size,
                                "uploaded_bytes": 0,
                                "last_update": time.time(),
                            }
                        self.upload_progress[upload_id][
                            "uploaded_bytes"
                        ] = uploaded_bytes
                        progress_pct = min(99, int(uploaded_bytes / file_size * 100))
                        self.upload_progress[upload_id]["progress"] = progress_pct
                        self.upload_progress[upload_id]["last_update"] = time.time()

        try:
            with open(file_path, "rb") as data:
                blob_client.upload_blob(
                    data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type),
                    max_concurrency=1,
                    raw_response_hook=progress_callback,
                )
            logger.info(
                f"Upload completed. callback_count={callback_count}, total bytes={uploaded_bytes}"
            )
            if upload_id:
                if progress_tracker:
                    progress_data = {
                        "status": "uploading",
                        "progress": 100,
                        "file_size": file_size,
                        "uploaded_bytes": file_size,
                        "stage": "finalizing",
                        "azure_status": "completed",
                    }
                    progress_tracker.update_progress(upload_id, progress_data)
                else:
                    with self.upload_lock:
                        if upload_id in self.upload_progress:
                            self.upload_progress[upload_id]["status"] = "completed"
                            self.upload_progress[upload_id]["progress"] = 100
                            self.upload_progress[upload_id][
                                "uploaded_bytes"
                            ] = file_size
                            self.upload_progress[upload_id]["last_update"] = time.time()
            account_name = self.blob_service_client.account_name
            account_key = self.blob_service_client.credential.account_key
            expiry_time = datetime.utcnow() + timedelta(hours=24)
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=self.container_name,
                blob_name=blob_path,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=expiry_time,
            )
            sas_url = f"https://{account_name}.blob.core.windows.net/{self.container_name}/{blob_path}?{sas_token}"
            return sas_url
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            if upload_id:
                if progress_tracker:
                    progress_data = {
                        "status": "error",
                        "azure_status": "error",
                        "error": str(e),
                    }
                    progress_tracker.update_progress(upload_id, progress_data)
                else:
                    with self.upload_lock:
                        if upload_id in self.upload_progress:
                            self.upload_progress[upload_id]["status"] = "error"
                            self.upload_progress[upload_id]["error"] = str(e)
            raise StorageError(
                f"Error uploading file to Azure storage: {str(e)}",
                file_path=file_path,
                blob_path=blob_path,
                container=self.container_name,
            )

    @log_service_call("BlobStorage")
    @retry_on_error(max_retries=2, retry_delay=1)
    def download_file(self, blob_path, local_path):
        """Download a blob to local disk."""
        if not blob_path:
            raise ValidationError("Blob path is required", field="blob_path")
        if not local_path:
            raise ValidationError("Local path is required", field="local_path")
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=blob_path
            )
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as download_file:
                download_data = blob_client.download_blob()
                download_file.write(download_data.readall())
            return local_path
        except Exception as e:
            raise StorageError(
                f"Error downloading blob: {str(e)}",
                blob_path=blob_path,
                local_path=local_path,
                container=self.container_name,
            )

    @log_service_call("BlobStorage")
    @retry_on_error(max_retries=3, retry_delay=1)
    def delete_blob(self, blob_path):
        """
        Delete a blob from Azure Blob Storage.

        Args:
            blob_path (str): path to the blob in storage

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if not blob_path:
            raise ValidationError("Blob path is required", field="blob_path")
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=blob_path
            )
            exists = blob_client.exists()
            if not exists:
                logger.warning(f"Blob {blob_path} not found, skipping deletion")
                return False
            blob_client.delete_blob()
            logger.info(f"Successfully deleted blob: {blob_path}")
            return True
        except Exception as e:
            raise StorageError(
                f"Error deleting blob: {str(e)}",
                blob_path=blob_path,
                container=self.container_name,
            )

    @log_service_call("BlobStorage")
    @retry_on_error(max_retries=3, retry_delay=1)
    def upload_bytes(self, data, blob_path, content_type=None):
        """
        Upload in-memory bytes directly to Azure, returning the SAS URL
        with read permission.
        """
        if not data:
            raise ValidationError("Data is required", field="data")
        if not blob_path:
            raise ValidationError("Blob path is required", field="blob_path")
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=blob_path
            )
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=(
                    ContentSettings(content_type=content_type) if content_type else None
                ),
            )
            account_name = self.blob_service_client.account_name
            account_key = self.blob_service_client.credential.account_key
            expiry_time = datetime.utcnow() + timedelta(hours=24)
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=self.container_name,
                blob_name=blob_path,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=expiry_time,
            )
            sas_url = f"https://{account_name}.blob.core.windows.net/{self.container_name}/{blob_path}?{sas_token}"
            return sas_url
        except Exception as e:
            raise StorageError(
                f"Error uploading bytes to Azure storage: {str(e)}",
                blob_path=blob_path,
                content_type=content_type,
                container=self.container_name,
            )

    def get_upload_progress(self, upload_id):
        """
        Return the current progress dict for a given upload_id
        """
        if not upload_id:
            raise ValidationError("Upload ID is required", field="upload_id")
        with self.upload_lock:
            return self.upload_progress.get(upload_id, None)

    def _get_content_type(self, file_path):
        """Return content type based on file extension for supported audio formats."""
        extension = os.path.splitext(file_path)[1].lower()
        content_types = {
            ".wav": "audio/wav",  # Covers WAV, ALAW/MULAW in WAV container
            ".mp3": "audio/mpeg",
            ".ogg": "audio/ogg",  # Covers OPUS/OGG
            ".opus": "audio/ogg",
            ".flac": "audio/flac",
            ".wma": "audio/x-ms-wma",
            ".aac": "audio/aac",
            ".amr": "audio/amr",
            ".webm": "audio/webm",
            ".m4a": "audio/mp4",
            ".spx": "audio/speex",  # SPEEX typically uses .spx extension
            ".json": "application/json",
            ".txt": "text/plain",
        }
        return content_types.get(extension, "application/octet-stream")
