"""
Integration tests for the UI routes.
"""
import pytest
from bs4 import BeautifulSoup

from app.models import File


class TestUIRoutes:
    """Tests for the UI routes."""

    def test_home_page(self, client):
        """Test the home page."""
        response = client.get('/')
        assert response.status_code == 200

        # Parse HTML to check content
        soup = BeautifulSoup(response.data, 'html.parser')

        # Check page title
        assert 'NSWCC Transcription Demo' in soup.title.text

        # Check for upload form
        assert soup.find('form', {'id': 'upload-form'}) is not None
        assert soup.find('input', {'type': 'file'}) is not None
        assert soup.find('button', {'type': 'submit'}) is not None

    def test_file_list_page(self, client, db_session):
        """Test the file list page."""
        # Create test files
        file1 = File(
            filename="test_file1.dcr",
            blob_url="https://example.com/blob/test_file1.dcr",
            status="completed",
            current_stage="transcribed",
            progress_percent=100.0,
            transcript_text="Test transcript 1"
        )
        file2 = File(
            filename="test_file2.dcr",
            blob_url="https://example.com/blob/test_file2.dcr",
            status="processing",
            current_stage="diarizing",
            progress_percent=60.0
        )

        db_session.add(file1)
        db_session.add(file2)
        db_session.commit()

        # Request the file list page
        response = client.get('/files')
        assert response.status_code == 200

        # Parse HTML to check content
        soup = BeautifulSoup(response.data, 'html.parser')

        # Check page title
        assert 'File List' in soup.title.text

        # Check that files are listed
        file_rows = soup.find_all('tr')
        assert len(file_rows) > 2  # Header row + at least 2 file rows

        # Check for file names in the table
        page_text = soup.get_text()
        assert 'test_file1.dcr' in page_text
        assert 'test_file2.dcr' in page_text

        # Check for status indicators
        assert 'completed' in page_text.lower()
        assert 'processing' in page_text.lower()

    def test_file_detail_page(self, client, db_session):
        """Test the file detail page."""
        # Create a test file with transcript
        file = File(
            filename="detail_test.dcr",
            blob_url="https://example.com/blob/detail_test.dcr",
            status="completed",
            current_stage="transcribed",
            progress_percent=100.0,
            transcript_text="SPEAKER_00: This is a test transcript.\n\nSPEAKER_01: With multiple speakers."
        )

        db_session.add(file)
        db_session.commit()

        # Request the file detail page
        response = client.get(f'/files/{file.id}')
        assert response.status_code == 200

        # Parse HTML to check content
        soup = BeautifulSoup(response.data, 'html.parser')

        # Check page title includes filename
        assert 'detail_test.dcr' in soup.title.text

        # Check for transcript content
        page_text = soup.get_text()
        assert 'SPEAKER_00' in page_text
        assert 'SPEAKER_01' in page_text
        assert 'This is a test transcript' in page_text
        assert 'With multiple speakers' in page_text

        # Check for metadata
        assert 'Status: completed' in page_text
        assert '100%' in page_text

    def test_file_detail_nonexistent(self, client):
        """Test accessing a non-existent file detail page."""
        response = client.get('/files/9999')
        assert response.status_code == 404

    def test_file_detail_processing(self, client, db_session):
        """Test accessing a file detail page for a file still processing."""
        # Create a test file that's still processing
        file = File(
            filename="processing_test.dcr",
            blob_url="https://example.com/blob/processing_test.dcr",
            status="processing",
            current_stage="transcribing",
            progress_percent=50.0
        )

        db_session.add(file)
        db_session.commit()

        # Request the file detail page
        response = client.get(f'/files/{file.id}')
        assert response.status_code == 200

        # Parse HTML to check content
        soup = BeautifulSoup(response.data, 'html.parser')

        # Check for processing indicator
        page_text = soup.get_text()
        assert 'Processing' in page_text
        assert '50%' in page_text

        # There should be no transcript yet
        assert 'Transcript not available' in page_text
