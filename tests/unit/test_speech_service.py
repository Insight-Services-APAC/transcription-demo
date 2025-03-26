"""
Unit tests for the SpeechService class.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from app.services.speech_service import SpeechService


class TestSpeechService:
    """Tests for the SpeechService class."""

    @pytest.fixture
    def speech_service(self):
        """Create a SpeechService instance with mocked Azure client."""
        with patch('app.services.speech_service.openai') as mock_openai:
            # Mock the OpenAI client response
            mock_openai.Client.return_value.audio.transcriptions.create.return_value = MagicMock(
                text="This is a test transcription."
            )

            service = SpeechService(
                api_key="test_api_key",
                api_endpoint="https://test-endpoint.openai.azure.com/",
                deployment_name="whisper"
            )
            yield service

    def test_initialization(self, speech_service):
        """Test that SpeechService initializes correctly."""
        assert speech_service.api_key == "test_api_key"
        assert speech_service.api_endpoint == "https://test-endpoint.openai.azure.com/"
        assert speech_service.deployment_name == "whisper"
        assert hasattr(speech_service, 'client')

    @patch('os.path.exists')
    def test_transcribe_audio(self, mock_exists, speech_service, sample_audio_file):
        """Test transcribing audio file."""
        # Setup
        mock_exists.return_value = True

        # Call the method
        result = speech_service.transcribe_audio(sample_audio_file)

        # Verify the result
        assert isinstance(result, dict)
        assert "text" in result
        assert result["text"] == "This is a test transcription."

        # Verify the OpenAI client was called
        speech_service.client.audio.transcriptions.create.assert_called_once()

    @patch('os.path.exists')
    def test_transcribe_audio_file_not_found(self, mock_exists, speech_service):
        """Test handling of file not found error."""
        # Setup
        mock_exists.return_value = False

        # Verify exception is raised
        with pytest.raises(FileNotFoundError):
            speech_service.transcribe_audio("nonexistent_file.wav")

    @patch('os.path.exists')
    def test_transcribe_audio_api_error(self, mock_exists, speech_service, sample_audio_file):
        """Test handling of API errors."""
        # Setup
        mock_exists.return_value = True

        # Mock an API error
        speech_service.client.audio.transcriptions.create.side_effect = Exception(
            "API Error")

        # Verify exception is raised and propagated
        with pytest.raises(Exception, match="API Error"):
            speech_service.transcribe_audio(sample_audio_file)

    @patch('os.path.exists')
    def test_transcribe_chunked_audio(self, mock_exists, speech_service):
        """Test transcribing multiple audio chunks."""
        # Setup
        mock_exists.return_value = True
        chunk_files = ["chunk1.wav", "chunk2.wav", "chunk3.wav"]

        # Call the method
        results = speech_service.transcribe_chunked_audio(chunk_files)

        # Verify the results
        assert len(results) == 3
        assert all(isinstance(result, dict) for result in results)
        assert all("text" in result for result in results)

        # Verify each chunk was processed
        assert speech_service.client.audio.transcriptions.create.call_count == 3
