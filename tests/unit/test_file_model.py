"""
Unit tests for the File model.
"""
import pytest
from datetime import datetime

from app.models import File


class TestFileModel:
    """Tests for the File database model."""

    def test_file_creation(self, db_session):
        """Test creating a new file record in the database."""
        # Create a new file
        new_file = File(
            filename="test_file.dcr",
            blob_url="https://example.com/blob/test_file.dcr",
            status="processing",
            current_stage="queued",
            progress_percent=0.0
        )

        # Add to session and commit
        db_session.add(new_file)
        db_session.commit()

        # Retrieve the file
        retrieved_file = db_session.query(File).filter_by(
            filename="test_file.dcr").first()

        # Verify the file was created
        assert retrieved_file is not None
        assert retrieved_file.filename == "test_file.dcr"
        assert retrieved_file.blob_url == "https://example.com/blob/test_file.dcr"
        assert retrieved_file.status == "processing"
        assert retrieved_file.current_stage == "queued"
        assert retrieved_file.progress_percent == 0.0
        assert retrieved_file.upload_time is not None

    def test_file_update(self, db_session):
        """Test updating a file record."""
        # Create a new file
        new_file = File(
            filename="update_test.dcr",
            blob_url="https://example.com/blob/update_test.dcr",
            status="processing",
            current_stage="queued",
            progress_percent=0.0
        )

        # Add to session and commit
        db_session.add(new_file)
        db_session.commit()

        # Update the file
        new_file.status = "completed"
        new_file.current_stage = "transcribed"
        new_file.progress_percent = 100.0
        new_file.transcript_url = "https://example.com/blob/transcript.txt"
        new_file.duration_seconds = "10.5"

        db_session.commit()

        # Retrieve the file
        retrieved_file = db_session.query(File).filter_by(
            filename="update_test.dcr").first()

        # Verify the updates
        assert retrieved_file.status == "completed"
        assert retrieved_file.current_stage == "transcribed"
        assert retrieved_file.progress_percent == 100.0
        assert retrieved_file.transcript_url == "https://example.com/blob/transcript.txt"
        assert retrieved_file.duration_seconds == "10.5"

    def test_file_delete(self, db_session):
        """Test deleting a file record."""
        # Create a new file
        new_file = File(
            filename="delete_test.dcr",
            blob_url="https://example.com/blob/delete_test.dcr",
            status="processing",
            current_stage="queued",
            progress_percent=0.0
        )

        # Add to session and commit
        db_session.add(new_file)
        db_session.commit()

        # Get the ID for later
        file_id = new_file.id

        # Delete the file
        db_session.delete(new_file)
        db_session.commit()

        # Try to retrieve the file
        retrieved_file = db_session.query(File).get(file_id)

        # Verify the file was deleted
        assert retrieved_file is None

    def test_file_timestamp_update(self, db_session):
        """Test that upload_time is set when a file is created."""
        # Create a new file
        new_file = File(
            filename="timestamp_test.dcr",
            blob_url="https://example.com/blob/timestamp_test.dcr",
            status="processing",
            current_stage="queued",
            progress_percent=0.0
        )

        # Add to session and commit
        db_session.add(new_file)
        db_session.commit()

        # Verify upload_time is set
        assert new_file.upload_time is not None
        assert isinstance(new_file.upload_time, datetime)

    def test_file_constraints(self, db_session):
        """Test model constraints."""
        # Test required fields
        with pytest.raises(Exception):  # SQLAlchemy will raise an exception
            # Missing required fields
            new_file = File()
            db_session.add(new_file)
            db_session.commit()

        # Rollback after expected failure
        db_session.rollback()

        # Test with minimal required fields
        new_file = File(
            filename="minimal_test.dcr",
            blob_url="https://example.com/blob/minimal_test.dcr"
        )

        # This should work with defaults
        db_session.add(new_file)
        db_session.commit()

        # Verify defaults were applied
        assert new_file.status == "uploaded"  # Default value from model
        assert new_file.progress_percent == 0.0  # Default value
