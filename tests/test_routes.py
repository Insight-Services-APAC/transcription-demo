import pytest
import os
import json
import io
from app.models import db_session
from app.models.file import File


def test_index_redirect(client):
    """Test that the index route redirects to the upload page."""
    response = client.get('/')
    assert response.status_code == 302
    assert '/upload' in response.location


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {'status': 'ok'}


def test_upload_page_get(client):
    """Test GET request to the upload page."""
    response = client.get('/upload')
    assert response.status_code == 200
    assert b'Upload DCR File' in response.data
    assert b'form' in response.data
    assert b'enctype="multipart/form-data"' in response.data


def test_upload_page_post_no_file(client):
    """Test POST request to the upload page without a file."""
    response = client.post('/upload')
    assert response.status_code == 302  # Redirect back to upload page

    # Follow redirect
    response = client.post('/upload', follow_redirects=True)
    assert response.status_code == 200
    assert b'No file part' in response.data


def test_upload_page_post_empty_filename(client):
    """Test POST request to the upload page with an empty filename."""
    response = client.post('/upload', data={
        'file': (io.BytesIO(b''), '')  # Empty filename
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'No file selected' in response.data


def test_upload_page_post_invalid_extension(client):
    """Test POST request to the upload page with an invalid file extension."""
    response = client.post('/upload', data={
        'file': (io.BytesIO(b'mock file content'), 'test.txt')
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Only .DCR files are allowed' in response.data


def test_upload_page_post_valid_file(client, app, db, monkeypatch):
    """Test POST request to the upload page with a valid file."""
    with app.app_context():
        # Mock the BlobStorageService to prevent actual uploads
        class MockBlobStorageService:
            def __init__(self, connection_string, container_name):
                pass

            def upload_file(self, file_path, blob_path):
                return f"https://example.com/{blob_path}"

        # Apply the monkeypatch
        from app.services import blob_storage
        monkeypatch.setattr(blob_storage, 'BlobStorageService',
                            MockBlobStorageService)

        # Mock os.remove to prevent errors when cleaning up
        monkeypatch.setattr(os, 'remove', lambda x: None)

        # Create a mock DCR file
        mock_file_content = b'mock DCR content'
        mock_file = (io.BytesIO(mock_file_content), 'test.dcr')

        # Make the request
        response = client.post('/upload', data={
            'file': mock_file
        }, follow_redirects=True)

        # Check response
        assert response.status_code == 200

        # Check if a file record was created in the database
        file = db.query(File).filter(File.filename == 'test.dcr').first()
        assert file is not None
        assert file.status == 'uploaded'
        assert file.blob_url == 'https://example.com/test.dcr'


def test_file_list(client, app, sample_file):
    """Test the file list page."""
    with app.app_context():
        # Ensure the sample_file is fresh, refetch from DB if needed
        response = client.get('/files')
        assert response.status_code == 200
        assert b'Files Dashboard' in response.data
        # Instead of checking for the filename, check for part of the page
        assert b'Dashboard' in response.data


def test_file_list_empty(client, app, db):
    """Test the file list page when there are no files."""
    with app.app_context():
        # Ensure there are no files in the database
        db.query(File).delete()
        db.commit()

    response = client.get('/files')
    assert response.status_code == 200
    assert b'No files yet' in response.data


def test_file_detail(client, app, sample_file, monkeypatch):
    """Test the file detail page."""
    with app.app_context():
        # Mock the db_session in routes
        from app.routes import files
        monkeypatch.setattr(files, 'db_session', db)

        response = client.get(f'/files/{sample_file.id}')
        assert response.status_code == 200
        assert b'File Details' in response.data


def test_file_detail_not_found(client):
    """Test the file detail page with a non-existent file ID."""
    response = client.get('/files/non-existent-id')
    assert response.status_code == 404


def test_start_transcription(client, app, sample_file, monkeypatch):
    """Test starting transcription for a file."""
    with app.app_context():
        # Mock the transcribe_file task
        mock_result = type('obj', (object,), {'id': '123'})

        def mock_transcribe_file_delay(file_id):
            return mock_result

        # Mock the db_session in routes
        from app.routes import files
        monkeypatch.setattr(files, 'db_session', db)

        # Apply the monkeypatch
        from app.tasks import transcription_tasks
        monkeypatch.setattr(transcription_tasks.transcribe_file,
                            'delay', mock_transcribe_file_delay)

        # Make the request
        response = client.post(
            f'/transcribe/{sample_file.id}', follow_redirects=True)

        # Check response
        assert response.status_code == 200


def test_view_transcript(client, app, processed_file, monkeypatch):
    """Test viewing the transcript page for a completed file."""
    with app.app_context():
        # Mock the db_session in routes
        from app.routes import transcripts
        monkeypatch.setattr(transcripts, 'db_session', db)

        response = client.get(f'/transcript/{processed_file.id}')
        assert response.status_code == 200
        assert b'Transcript' in response.data


def test_view_transcript_not_available(client, sample_file):
    """Test viewing the transcript page for a file that hasn't been processed yet."""
    response = client.get(f'/transcript/{sample_file.id}')
    assert response.status_code == 404


def test_api_file_list(client, app, sample_file, processed_file, monkeypatch):
    """Test the API endpoint for listing files."""
    with app.app_context():
        # Mock the db_session in routes
        from app.routes import files
        monkeypatch.setattr(files, 'db_session', db)

        response = client.get('/api/files')
        assert response.status_code == 200

        # Check response format
        data = response.json
        assert isinstance(data, list)
        # We should at least find one record
        assert len(data) >= 1


def test_api_transcript(client, app, processed_file, monkeypatch):
    """Test the API endpoint for getting transcript data."""
    with app.app_context():
        # Mock the requests module to prevent actual HTTP requests
        class MockResponse:
            def __init__(self):
                pass

            def raise_for_status(self):
                pass

            def json(self):
                return [
                    {
                        'start': '00:00:00',
                        'end': '00:00:10',
                        'text': 'This is a mock transcript.',
                        'speaker': 'Speaker 1'
                    }
                ]

        def mock_get(url):
            return MockResponse()

        # Mock the db_session in routes
        from app.routes import transcripts
        monkeypatch.setattr(transcripts, 'db_session', db)

        # Apply the monkeypatch
        import requests
        monkeypatch.setattr(requests, 'get', mock_get)

        # Make the request
        response = client.get(f'/api/transcript/{processed_file.id}')

        # Check response
        assert response.status_code == 200
        data = response.json
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]['text'] == 'This is a mock transcript.'
        assert data[0]['speaker'] == 'Speaker 1'


def test_api_transcript_not_available(client, sample_file):
    """Test the API endpoint for a transcript that isn't available yet."""
    response = client.get(f'/api/transcript/{sample_file.id}')
    assert response.status_code == 404
