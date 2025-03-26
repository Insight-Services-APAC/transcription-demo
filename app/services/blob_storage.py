import os
from azure.storage.blob import BlobServiceClient, ContentSettings
from werkzeug.utils import secure_filename

class BlobStorageService:
    def __init__(self, connection_string, container_name):
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = container_name
        
        # Create container if it doesn't exist
        try:
            self.blob_service_client.create_container(self.container_name)
        except Exception as e:
            # Container may already exist, which is fine
            pass
            
    def upload_file(self, file_path, blob_path):
        """
        Upload a file from a local path to Azure Blob Storage
        
        Args:
            file_path (str): Path to local file
            blob_path (str): Path in blob storage
            
        Returns:
            str: URL of the uploaded blob
        """
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )
        
        # Determine content type based on file extension
        content_type = self._get_content_type(file_path)
        
        with open(file_path, "rb") as data:
            blob_client.upload_blob(
                data, 
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type)
            )
            
        return blob_client.url
    
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