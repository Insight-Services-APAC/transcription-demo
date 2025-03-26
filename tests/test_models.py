import pytest
from app.models import db_session
from app.models.file import File
import uuid


def test_file_creation(app, db):
    """Test creating a file record in the database."""
    with app.app_context():
        # Create a new file record
        file_id = str(uuid.uuid4())
        file = File(
            id=file_id,
            filename='test_file.dcr',
            blob_url='https://example.com/test_file.dcr'
        )

        # Add to session and commit
        db.add(file)
        db.commit()

        # Query the file and check if it exists
        queried_file = db.query(File).filter(File.id == file_id).first()

        assert queried_file is not None
        assert queried_file.id == file_id
        assert queried_file.filename == 'test_file.dcr'
        assert queried_file.blob_url == 'https://example.com/test_file.dcr'
        assert queried_file.status == 'uploaded'  # Default status

        # Clean up
        db.delete(file)
        db.commit()


def test_file_update(app, sample_file, db):
    """Test updating a file record."""
    with app.app_context():
        # Update the file status
        sample_file.status = 'processing'
        db.commit()

        # Query the file again and check if the status has been updated
        updated_file = db.query(File).filter(
            File.id == sample_file.id).first()

        assert updated_file.status == 'processing'

        # Update more attributes
        updated_file.audio_url = 'https://example.com/test_file.wav'
        updated_file.speaker_count = '2'
        db.commit()

        # Query again and check if all attributes have been updated
        final_file = db.query(File).filter(
            File.id == sample_file.id).first()

        assert final_file.audio_url == 'https://example.com/test_file.wav'
        assert final_file.speaker_count == '2'


def test_file_to_dict(app, processed_file):
    """Test the to_dict method of the File model."""
    with app.app_context():
        # Call to_dict on the processed file
        file_dict = processed_file.to_dict()

        # Check if all expected keys are present
        expected_keys = [
            'id', 'filename', 'upload_time', 'status', 'error_message',
            'blob_url', 'audio_url', 'transcript_url', 'diarization_url',
            'duration_seconds', 'speaker_count'
        ]

        for key in expected_keys:
            assert key in file_dict

        # Check specific values
        assert file_dict['id'] == processed_file.id
        assert file_dict['filename'] == 'processed_file.dcr'
        assert file_dict['status'] == 'completed'
        assert file_dict['speaker_count'] == '3'
