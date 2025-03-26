"""
Unit tests for the BlobStorageService.
"""
import os
import pytest
import threading
import time
import uuid
from unittest.mock import MagicMock, patch

from app.services.blob_storage import BlobStorageService


class TestBlobStorageService:
    """Tests for the BlobStorageService class."""

    @pytest.fixture
    def blob_service(self):
        """Create a BlobStorageService instance with mocked Azure client."""
        with patch('app.services.blob_storage.BlobServiceClient') as mock_client:
            # Configure the mock
            mock_blob_client = MagicMock()
            mock_client.from_connection_string.return_value.get_blob_client.return_value = mock_blob_client
            mock_blob_client.url = "https://example.com/test-blob"

            # Create the service with mock objects
            service = BlobStorageService(
                connection_string="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;EndpointSuffix=core.windows.net",
                container_name="test-container"
            )

            # Replace the blob_service_client with our mock
            service.blob_service_client = mock_client.from_connection_string.return_value

            yield service

    def test_initialization(self, blob_service):
        """Test that the BlobStorageService initializes correctly."""
        assert blob_service.container_name == "test-container"
        assert isinstance(blob_service.upload_progress, dict)
        # Lock objects have acquire method
        assert hasattr(blob_service.upload_lock, 'acquire')
        assert hasattr(blob_service.upload_lock,
                       'release')  # and release method

    def test_upload_file(self, blob_service, tmp_path):
        """Test uploading a file to blob storage."""
        # Create a temporary file
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("This is test content")

        # Generate a random upload ID
        upload_id = str(uuid.uuid4())

        # Upload the file
        result = blob_service.upload_file(
            str(test_file), "test_destination.txt", upload_id)

        # Verify the result
        assert result == "https://example.com/test-blob"

        # Verify the progress tracking
        assert upload_id in blob_service.upload_progress
        assert blob_service.upload_progress[upload_id]['status'] == 'completed'
        assert blob_service.upload_progress[upload_id]['progress'] == 100

    def test_get_upload_progress(self, blob_service):
        """Test getting upload progress."""
        # Setup test data
        upload_id = str(uuid.uuid4())
        blob_service.upload_progress[upload_id] = {
            'status': 'uploading',
            'progress': 50,
            'started_at': '2023-01-01T00:00:00',
            'file_size': 1000,
            'uploaded_bytes': 500,
            'last_update': time.time()
        }

        # Get the progress
        progress = blob_service.get_upload_progress(upload_id)

        # Verify the progress data
        assert progress['status'] == 'uploading'
        assert progress['progress'] == 50
        assert progress['file_size'] == 1000
        assert progress['uploaded_bytes'] == 500

    def test_get_upload_progress_not_found(self, blob_service):
        """Test getting upload progress for non-existent upload."""
        upload_id = str(uuid.uuid4())
        progress = blob_service.get_upload_progress(upload_id)
        assert progress is None

    def test_get_blob_url(self, blob_service):
        """Test getting a blob URL."""
        url = blob_service.get_blob_url("test_blob.txt")
        assert url == "https://example.com/test-blob"

    def test_content_type_detection(self, blob_service):
        """Test detection of content types based on file extension."""
        assert blob_service._get_content_type("test.txt") == "text/plain"
        assert blob_service._get_content_type("test.pdf") == "application/pdf"
        assert blob_service._get_content_type("test.jpg") == "image/jpeg"
        assert blob_service._get_content_type(
            "test.unknown") == "application/octet-stream"

    def test_upload_progress_thread_safety(self, blob_service, tmp_path):
        """Test that progress tracking is thread-safe."""
        # Create a temporary file
        test_file = tmp_path / "test_file.txt"
        # Make it reasonably large
        test_file.write_text("This is test content" * 1000)

        # Generate random upload IDs
        upload_id1 = str(uuid.uuid4())
        upload_id2 = str(uuid.uuid4())

        # Simulate concurrent uploads
        def upload_task(upload_id):
            blob_service.upload_file(
                str(test_file), f"test_{upload_id}.txt", upload_id)

        # Start concurrent threads
        thread1 = threading.Thread(target=upload_task, args=(upload_id1,))
        thread2 = threading.Thread(target=upload_task, args=(upload_id2,))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Verify both uploads completed
        assert upload_id1 in blob_service.upload_progress
        assert upload_id2 in blob_service.upload_progress
        assert blob_service.upload_progress[upload_id1]['status'] == 'completed'
        assert blob_service.upload_progress[upload_id2]['status'] == 'completed'
