import os
import time
from azure.storage.blob import (
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
    BlobSasPermissions
)
from werkzeug.utils import secure_filename
import datetime
import threading
import json


class BlobStorageService:
    def __init__(self, connection_string, container_name):
        """
        Initialize BlobStorageService with an Azure Storage connection string
        and container name. We'll generate SAS URLs after we upload files.
        """
        self.blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )
        self.container_name = container_name
        self.upload_progress = {}
        self.upload_lock = threading.Lock()

        print(f"BlobStorageService initialized (thread ID: {threading.get_ident()})")

        # Create container if it doesn't exist
        try:
            self.blob_service_client.create_container(self.container_name)
        except Exception:
            # Likely the container already exists; ignore
            pass

    def upload_file(self, file_path, blob_path, upload_id=None):
        """
        Upload a file from local path to Azure Blob Storage and then
        generate a read-only SAS URL that the Speech API can use.
        
        Args:
            file_path (str): path to local file
            blob_path (str): desired path/name in blob storage
            upload_id (str, optional): ID for tracking progress

        Returns:
            str: A SAS URL for the uploaded blob (with read permission).
        """
        import threading

        # We'll store the final SAS URL in a local variable
        sas_url = None

        print(f"Starting upload_file: file_path={file_path}, blob_path={blob_path}, upload_id={upload_id}, thread={threading.get_ident()}")

        # Build the BlobClient
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )

        # Decide content-type from extension
        content_type = self._get_content_type(file_path)
        file_size = os.path.getsize(file_path)
        print(f"Uploading file of size {file_size} bytes with content-type={content_type}")

        # Track progress
        uploaded_bytes = 0
        callback_count = 0

        def progress_callback(current):
            nonlocal uploaded_bytes, callback_count

            callback_count += 1
            if hasattr(current, "context") and hasattr(current.context, "data_read"):
                # In some newer azure libraries, 'current' can be a PipelineResponse
                current = getattr(current.context, "data_read", 1024)
            elif not isinstance(current, (int, float)):
                current = 1024  # fallback

            uploaded_bytes += current
            with self.upload_lock:
                if upload_id:
                    if upload_id not in self.upload_progress:
                        self.upload_progress[upload_id] = {
                            "status": "uploading",
                            "progress": 0,
                            "file_size": file_size,
                            "uploaded_bytes": 0,
                            "last_update": time.time(),
                        }
                    # Update the tracking dictionary
                    self.upload_progress[upload_id]["uploaded_bytes"] = uploaded_bytes
                    progress_pct = min(99, int((uploaded_bytes / file_size) * 100))
                    self.upload_progress[upload_id]["progress"] = progress_pct
                    self.upload_progress[upload_id]["last_update"] = time.time()

        try:
            with open(file_path, "rb") as data:
                blob_client.upload_blob(
                    data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type),
                    max_concurrency=1,
                    raw_response_hook=progress_callback
                )

            print(f"Upload completed. callback_count={callback_count}, total bytes={uploaded_bytes}")

            # Mark upload as done if we were tracking
            if upload_id:
                with self.upload_lock:
                    if upload_id in self.upload_progress:
                        self.upload_progress[upload_id]["status"] = "completed"
                        self.upload_progress[upload_id]["progress"] = 100
                        self.upload_progress[upload_id]["uploaded_bytes"] = file_size
                        self.upload_progress[upload_id]["last_update"] = time.time()

            # Now generate a read-only SAS URL for the uploaded blob
            account_name = self.blob_service_client.account_name
            # We assume the service client is authenticated by account key
            account_key = self.blob_service_client.credential.account_key

            expiry_time = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=self.container_name,
                blob_name=blob_path,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=expiry_time
            )

            # Construct the final SAS URL
            sas_url = f"https://{account_name}.blob.core.windows.net/{self.container_name}/{blob_path}?{sas_token}"
            print(f"Generated SAS URL: {sas_url}")

            return sas_url

        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            if upload_id:
                with self.upload_lock:
                    if upload_id in self.upload_progress:
                        self.upload_progress[upload_id]["status"] = "error"
                        self.upload_progress[upload_id]["error"] = str(e)
            raise e

    def download_file(self, blob_path, local_path):
        """Download a blob to local disk."""
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name, blob=blob_path
        )
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as download_file:
            download_data = blob_client.download_blob()
            download_file.write(download_data.readall())
        return local_path

    def upload_bytes(self, data, blob_path, content_type=None):
        """
        Upload in-memory bytes directly to Azure, returning the SAS URL
        with read permission.
        """
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )
        from datetime import datetime, timedelta

        # Upload
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type) if content_type else None
        )

        # Generate SAS
        account_name = self.blob_service_client.account_name
        account_key = self.blob_service_client.credential.account_key
        expiry_time = datetime.datetime.utcnow() + datetime.timedelta(hours=24)

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=self.container_name,
            blob_name=blob_path,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry_time
        )
        sas_url = f"https://{account_name}.blob.core.windows.net/{self.container_name}/{blob_path}?{sas_token}"
        return sas_url

    def get_upload_progress(self, upload_id):
        """
        Return the current progress dict for a given upload_id
        """
        with self.upload_lock:
            return self.upload_progress.get(upload_id, None)

    def _get_content_type(self, file_path):
        """Pick a simple content type based on file extension."""
        extension = os.path.splitext(file_path)[1].lower()
        content_types = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".json": "application/json",
            ".txt": "text/plain",
        }
        return content_types.get(extension, "application/octet-stream")
