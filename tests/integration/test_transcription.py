"""
Integration tests for the transcription process.
"""
import os
import pytest
import json
from unittest.mock import patch, MagicMock

from app.models import File
from app.tasks.transcription_tasks import transcribe_file


class TestTranscriptionFlow:
    """Integration tests for the transcription flow."""

    @pytest.fixture
    def mock_services(self):
        """Mock all services used in the transcription flow."""
        with patch('app.tasks.transcription.AudioProcessor') as mock_audio:
            with patch('app.tasks.transcription.SpeechService') as mock_speech:
                with patch('app.tasks.transcription.DiarizationService') as mock_diarization:
                    with patch('app.tasks.transcription.TranscriptStitcher') as mock_stitcher:
                        # Configure AudioProcessor mock
                        mock_audio.return_value.extract_audio.return_value = "/tmp/test_audio.wav"
                        mock_audio.return_value.split_audio.return_value = [
                            "/tmp/chunk1.wav", "/tmp/chunk2.wav"]

                        # Configure SpeechService mock
                        mock_speech.return_value.transcribe_chunked_audio.return_value = [
                            {"text": "This is a test."},
                            {"text": "This is more test content."}
                        ]

                        # Configure DiarizationService mock
                        mock_diarization.return_value.diarize.return_value = [
                            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
                            {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_01"}
                        ]

                        # Configure TranscriptStitcher mock
                        mock_stitcher.return_value.stitch_transcript.return_value = [
                            {"text": "This is a test.", "speaker": "SPEAKER_00",
                                "start": 0.0, "end": 5.0},
                            {"text": "This is more test content.",
                                "speaker": "SPEAKER_01", "start": 5.0, "end": 10.0}
                        ]
                        mock_stitcher.return_value.format_transcript.return_value = (
                            "SPEAKER_00: This is a test.\n\n"
                            "SPEAKER_01: This is more test content."
                        )

                        yield {
                            "audio": mock_audio,
                            "speech": mock_speech,
                            "diarization": mock_diarization,
                            "stitcher": mock_stitcher
                        }

    def test_transcribe_file_task(self, db_session, mock_services):
        """Test the transcribe_file Celery task."""
        # Create a test file record
        file_record = File(
            filename="test_transcribe.dcr",
            blob_url="https://example.com/blob/test_transcribe.dcr",
            status="processing",
            current_stage="queued"
        )
        db_session.add(file_record)
        db_session.commit()

        file_id = file_record.id

        # Run the transcription task
        transcribe_file(file_id)

        # Refresh the file record
        db_session.refresh(file_record)

        # Verify the file was updated correctly
        assert file_record.status == "completed"
        assert file_record.current_stage == "transcribed"
        assert file_record.progress_percent == 100.0
        assert file_record.transcript_text is not None
        assert "SPEAKER_00" in file_record.transcript_text
        assert "SPEAKER_01" in file_record.transcript_text
        assert file_record.transcription_time is not None

        # Verify all services were called correctly
        mock_services["audio"].return_value.extract_audio.assert_called_once()
        mock_services["audio"].return_value.split_audio.assert_called_once()
        mock_services["speech"].return_value.transcribe_chunked_audio.assert_called_once()
        mock_services["diarization"].return_value.diarize.assert_called_once()
        mock_services["stitcher"].return_value.stitch_transcript.assert_called_once()
        mock_services["stitcher"].return_value.format_transcript.assert_called_once()

    def test_transcribe_nonexistent_file(self, db_session, mock_services):
        """Test transcribing a file that doesn't exist in the database."""
        # Use a non-existent file ID
        file_id = 9999

        # Run the transcription task
        # This should log an error but not raise an exception
        transcribe_file(file_id)

        # Verify no services were called
        mock_services["audio"].return_value.extract_audio.assert_not_called()
        mock_services["speech"].return_value.transcribe_chunked_audio.assert_not_called()
        mock_services["diarization"].return_value.diarize.assert_not_called()
        mock_services["stitcher"].return_value.stitch_transcript.assert_not_called()

    @patch('app.tasks.transcription.download_blob')
    def test_transcribe_file_with_service_error(self, mock_download_blob, db_session, mock_services):
        """Test handling of service errors during transcription."""
        # Create a test file record
        file_record = File(
            filename="test_error.dcr",
            blob_url="https://example.com/blob/test_error.dcr",
            status="processing",
            current_stage="queued"
        )
        db_session.add(file_record)
        db_session.commit()

        file_id = file_record.id

        # Set up the download_blob mock
        mock_download_blob.return_value = "/tmp/test_error.dcr"

        # Mock an error in the audio extraction
        mock_services["audio"].return_value.extract_audio.side_effect = Exception(
            "Audio extraction failed")

        # Run the transcription task
        transcribe_file(file_id)

        # Refresh the file record
        db_session.refresh(file_record)

        # Verify the file was updated with error status
        assert file_record.status == "error"
        assert "Audio extraction failed" in file_record.error_message

    def test_file_api_endpoints(self, client, db_session):
        """Test the file API endpoints."""
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

        # Test file list endpoint
        response = client.get('/api/files')
        assert response.status_code == 200
        file_list = json.loads(response.data)
        assert len(file_list) >= 2  # At least our 2 test files

        # Test individual file endpoint
        response = client.get(f'/api/files/{file1.id}')
        assert response.status_code == 200
        file_data = json.loads(response.data)
        assert file_data['id'] == file1.id
        assert file_data['filename'] == "test_file1.dcr"
        assert file_data['status'] == "completed"
        assert file_data['transcript_text'] == "Test transcript 1"

        # Test non-existent file
        response = client.get('/api/files/9999')
        assert response.status_code == 404
