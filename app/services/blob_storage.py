import os
import time
from azure.storage.blob import BlobServiceClient, ContentSettings
from werkzeug.utils import secure_filename
import datetime
import threading
import json

class BlobStorageService:
    def __init__(self, connection_string, container_name):
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = container_name
        self.upload_progress = {}
        self.upload_lock = threading.Lock()
        
        # Create container if it doesn't exist
        try:
            self.blob_service_client.create_container(self.container_name)
        except Exception as e:
            # Container may already exist, which is fine
            pass
            
    def upload_file(self, file_path, blob_path, upload_id=None):
        """
        Upload a file from a local path to Azure Blob Storage
        
        Args:
            file_path (str): Path to local file
            blob_path (str): Path in blob storage
            upload_id (str, optional): ID for tracking progress
            
        Returns:
            str: URL of the uploaded blob
        """
        # Initialize progress tracking if upload_id is provided
        if upload_id:
            with self.upload_lock:
                self.upload_progress[upload_id] = {
                    'status': 'uploading',
                    'progress': 0,
                    'started_at': datetime.datetime.now().isoformat(),
                    'file_size': os.path.getsize(file_path),
                    'uploaded_bytes': 0,
                    'last_update': time.time()
                }
        
        # Get file size for progress calculation
        file_size = os.path.getsize(file_path)
        print(f"Uploading file: {file_path}, Size: {file_size / (1024*1024):.2f} MB")
        
        # Get blob client
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )
        
        # Determine content type based on file extension
        content_type = self._get_content_type(file_path)
        
        # Track upload progress
        uploaded_bytes = 0
        last_percentage = 0
        
        # Fixed progress_callback function that properly handles PipelineResponse objects
        def progress_callback(response):
            nonlocal uploaded_bytes, last_percentage
            
            # If response is a pipeline response, we need to get the actual bytes from it
            # Azure SDK may pass either an int or a PipelineResponse object
            if hasattr(response, 'context'):
                # This is a PipelineResponse
                try:
                    # Try to get bytes from context
                    current = getattr(response.context, 'data_read', 0)
                except Exception as e:
                    # If we can't get this info, just use a small increment
                    print(f"Progress callback error: {str(e)}")
                    current = 1024  # Default to 1KB increment
            else:
                # This is just a number
                current = response
            
            # Update total bytes
            uploaded_bytes += current
            percentage = min(99, int((uploaded_bytes / file_size) * 100))  # Cap at 99% until complete
            
            # Update progress in memory
            if upload_id:
                with self.upload_lock:
                    if upload_id in self.upload_progress:
                        self.upload_progress[upload_id]['progress'] = percentage
                        self.upload_progress[upload_id]['uploaded_bytes'] = uploaded_bytes
                        self.upload_progress[upload_id]['last_update'] = time.time()
            
            # Log progress at reasonable intervals
            if percentage > last_percentage:
                # Calculate upload speed
                if upload_id and upload_id in self.upload_progress:
                    elapsed = time.time() - self.upload_progress[upload_id]['last_update']
                    if elapsed > 0:
                        speed = current / elapsed / 1024 / 1024  # MB/s
                        eta = (file_size - uploaded_bytes) / (current / elapsed) if current > 0 else 0
                        eta_str = str(datetime.timedelta(seconds=int(eta)))
                        print(f"Upload progress: {percentage}% ({uploaded_bytes / (1024*1024):.2f} MB / {file_size / (1024*1024):.2f} MB) - {speed:.2f} MB/s - ETA: {eta_str}")
                last_percentage = percentage
        
        try:
            # Upload with progress tracking
            with open(file_path, "rb") as data:
                blob_client.upload_blob(
                    data, 
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type),
                    max_concurrency=4,  # Limit concurrent connections
                    raw_response_hook=progress_callback
                )
            
            # Update status to completed
            if upload_id:
                with self.upload_lock:
                    if upload_id in self.upload_progress:
                        self.upload_progress[upload_id]['status'] = 'completed'
                        self.upload_progress[upload_id]['progress'] = 100
                        self.upload_progress[upload_id]['uploaded_bytes'] = file_size
            
            return blob_client.url
            
        except Exception as e:
            # Update status to error
            if upload_id:
                with self.upload_lock:
                    if upload_id in self.upload_progress:
                        self.upload_progress[upload_id]['status'] = 'error'
                        self.upload_progress[upload_id]['error'] = str(e)
            
            print(f"Upload error: {str(e)}")
            raise e
    
    def upload_bytes(self, data, blob_path, content_type=None):
        """Upload bytes data to Azure Blob Storage"""
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )
        
        # Set content type if provided
        content_settings = None
        if content_type:
            content_settings = ContentSettings(content_type=content_type)
            
        blob_client.upload_blob(
            data, 
            overwrite=True,
            content_settings=content_settings
        )
            
        return blob_client.url
    
    def download_file(self, blob_path, local_path):
        """Download a file from Azure Blob Storage"""
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )
        
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        with open(local_path, "wb") as download_file:
            download_data = blob_client.download_blob()
            download_file.write(download_data.readall())
            
        return local_path
    
    def get_blob_url(self, blob_path):
        """Get the URL for a blob"""
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )
        return blob_client.url
    
    def get_upload_progress(self, upload_id):
        """Get the current progress of an upload"""
        try:
            with self.upload_lock:
                if upload_id in self.upload_progress:
                    # Make a copy of the progress data to avoid thread issues
                    progress_data = {
                        'status': self.upload_progress[upload_id].get('status', 'unknown'),
                        'progress': self.upload_progress[upload_id].get('progress', 0),
                        'started_at': self.upload_progress[upload_id].get('started_at', ''),
                        'file_size': self.upload_progress[upload_id].get('file_size', 0),
                        'uploaded_bytes': self.upload_progress[upload_id].get('uploaded_bytes', 0),
                        'last_update': self.upload_progress[upload_id].get('last_update', 0)
                    }
                    
                    # Check for error
                    if 'error' in self.upload_progress[upload_id]:
                        progress_data['error'] = self.upload_progress[upload_id]['error']
                    
                    return progress_data
                else:
                    return None
        except Exception as e:
            print(f"Error getting upload progress: {str(e)}")
            # Return a basic progress object that won't cause client-side issues
            return {
                'status': 'error',
                'progress': 0,
                'error': f'Error tracking progress: {str(e)}',
                'file_size': 0,
                'uploaded_bytes': 0
            }
    
    def cleanup_progress(self, upload_id):
        """Remove a completed or errored upload from progress tracking"""
        with self.upload_lock:
            if upload_id in self.upload_progress:
                # Only remove if status is completed or error
                status = self.upload_progress[upload_id]['status']
                if status in ['completed', 'error']:
                    del self.upload_progress[upload_id]
                    return True
            return False
    
    def _get_content_type(self, file_path):
        """Determine content type based on file extension"""
        extension = os.path.splitext(file_path)[1].lower()
        content_types = {
            '.dcr': 'application/octet-stream',
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.json': 'application/json',
            '.txt': 'text/plain'
        }
        return content_types.get(extension, 'application/octet-stream')