"""
Integration tests for the file upload functionality.
"""
import os
import pytest
import tempfile
import json
import time
from unittest.mock import patch, MagicMock
from io import BytesIO

from app.models import File


class TestFileUpload:
    """Integration tests for file upload functionality."""

    @pytest.fixture
    def test_dcr_file(self):
        """Create a test DCR file for uploads."""
        with tempfile.NamedTemporaryFile(suffix='.dcr', delete=False) as f:
            f.write(b'TESTDCRFILECONTENTS')
            filepath = f.name

        yield filepath

        # Clean up the test file
        if os.path.exists(filepath):
            os.unlink(filepath)

    @patch('app.routes.files.upload_to_azure')
    def test_upload_file(self, mock_upload_to_azure, client, test_dcr_file):
        """Test uploading a file through the API."""
        # Mock the upload_to_azure background task
        mock_upload_to_azure.return_value = None

        # Create a file object for upload
        with open(test_dcr_file, 'rb') as f:
            data = {
                'file': (BytesIO(f.read()), 'test.dcr'),
            }

        # Make the upload request
        response = client.post(
            '/api/files/upload',
            data=data,
            content_type='multipart/form-data'
        )

        # Check the response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert 'upload_id' in response_data
        assert 'message' in response_data
        assert 'success' in response_data
        assert response_data['success'] is True

        # Verify the background task was triggered
        mock_upload_to_azure.assert_called_once()

    @patch('app.routes.files.upload_to_azure')
    def test_upload_invalid_file_type(self, mock_upload_to_azure, client):
        """Test uploading a file with an invalid extension."""
        # Create an invalid file for upload
        with tempfile.NamedTemporaryFile(suffix='.txt') as f:
            f.write(b'INVALID FILE TYPE')
            f.seek(0)

            data = {
                'file': (BytesIO(f.read()), 'test.txt'),
            }

        # Make the upload request
        response = client.post(
            '/api/files/upload',
            data=data,
            content_type='multipart/form-data'
        )

        # Check the response
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data
        assert 'Invalid file type' in response_data['error']

        # Verify the background task was not triggered
        mock_upload_to_azure.assert_not_called()

    @patch('app.services.blob_storage.BlobStorageService')
    def test_upload_progress_tracking(self, mock_blob_service, client, app):
        """Test tracking upload progress."""
        # Create a unique upload ID
        import uuid
        upload_id = str(uuid.uuid4())

        # Mock data for upload progress
        mock_progress_data = {
            'status': 'uploading',
            'progress': 50,
            'file_size': 1000,
            'uploaded_bytes': 500,
            'last_update': time.time()
        }

        # Mock the get_upload_progress method
        mock_instance = mock_blob_service.return_value
        mock_instance.get_upload_progress.return_value = mock_progress_data

        # Store upload data in local_uploads
        with app.app_context():
            from app.routes.files import local_uploads
            local_uploads[upload_id] = {
                'azure_status': 'in_progress',
                'start_time': time.time()
            }

        # Request progress
        response = client.get(f'/upload/progress/{upload_id}')

        # Check the response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['status'] == 'uploading'
        assert response_data['progress'] == 50

    @patch('app.services.blob_storage.BlobStorageService')
    def test_completed_upload_redirect(self, mock_blob_service, client, app, db_session):
        """Test redirect after upload completion."""
        # Create a unique upload ID
        import uuid
        upload_id = str(uuid.uuid4())

        # Create a test file record
        file_record = File(
            filename="test_redirect.dcr",
            blob_url="https://example.com/blob/test_redirect.dcr",
            status="processing",
            current_stage="queued"
        )
        db_session.add(file_record)
        db_session.commit()

        # Store upload data in local_uploads with completed status
        with app.app_context():
            from app.routes.files import local_uploads
            local_uploads[upload_id] = {
                'azure_status': 'completed',
                'file_id': file_record.id,
                'start_time': time.time()
            }

        # Request progress (should get redirect)
        response = client.get(f'/upload/progress/{upload_id}')

        # Check the response
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['status'] == 'completed'
        assert response_data['progress'] == 100
        assert 'redirect_url' in response_data
        assert str(file_record.id) in response_data['redirect_url']
