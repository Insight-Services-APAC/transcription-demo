"""
Unit tests for the AudioProcessor service.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from app.services.audio_processor import AudioProcessor


class TestAudioProcessor:
    """Tests for the AudioProcessor class."""

    @pytest.fixture
    def audio_processor(self):
        """Create an instance of AudioProcessor with mocked subprocess."""
        with patch('app.services.audio_processor.subprocess') as mock_subprocess:
            mock_subprocess.run.return_value.returncode = 0
            processor = AudioProcessor()
            yield processor

    def test_initialization(self, audio_processor):
        """Test that AudioProcessor initializes correctly."""
        assert hasattr(audio_processor, 'extract_audio')
        assert hasattr(audio_processor, 'split_audio')

    @patch('os.path.exists')
    @patch('app.services.audio_processor.subprocess.run')
    def test_extract_audio(self, mock_run, mock_exists, sample_dcr_file):
        """Test extracting audio from DCR file."""
        # Setup
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        processor = AudioProcessor()
        output_file = processor.extract_audio(sample_dcr_file)

        # Verify
        assert output_file.endswith('.wav')
        mock_run.assert_called_once()

        # Clean up the test WAV file that might have been created
        if os.path.exists(output_file):
            os.remove(output_file)

    @patch('os.path.exists')
    @patch('app.services.audio_processor.subprocess.run')
    def test_extract_audio_failure(self, mock_run, mock_exists, sample_dcr_file):
        """Test handling of extraction failure."""
        # Setup
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=1)

        processor = AudioProcessor()

        # Verify that exception is raised on command failure
        with pytest.raises(Exception):
            processor.extract_audio(sample_dcr_file)

    @patch('os.path.exists')
    @patch('app.services.audio_processor.subprocess.run')
    def test_split_audio(self, mock_run, mock_exists, sample_audio_file):
        """Test splitting audio into chunks."""
        # Setup
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        processor = AudioProcessor()

        # Create test output directory
        os.makedirs(os.path.dirname(sample_audio_file) +
                    "/output", exist_ok=True)

        # Mock audio duration to avoid actual file analysis
        with patch.object(processor, '_get_audio_duration', return_value=30.0):
            chunk_files = processor.split_audio(
                sample_audio_file, chunk_size=10)

        # Verify
        # With 30s audio and 10s chunks, we expect 3 chunks
        assert len(chunk_files) == 3
        assert all(".wav" in chunk for chunk in chunk_files)

        # Clean up any created files
        for chunk in chunk_files:
            if os.path.exists(chunk):
                os.remove(chunk)

    @patch('os.path.exists')
    @patch('app.services.audio_processor.subprocess.run')
    def test_get_audio_duration(self, mock_run, mock_exists, sample_audio_file):
        """Test getting audio duration."""
        # Setup
        mock_exists.return_value = True
        # Mock ffprobe output with sample duration info
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"format": {"duration": "15.5"}}'
        )

        processor = AudioProcessor()
        duration = processor._get_audio_duration(sample_audio_file)

        # Verify
        assert duration == 15.5
        mock_run.assert_called_once()

    @patch('os.path.exists')
    @patch('app.services.audio_processor.subprocess.run')
    def test_get_audio_duration_failure(self, mock_run, mock_exists, sample_audio_file):
        """Test handling of duration extraction failure."""
        # Setup
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=1)

        processor = AudioProcessor()

        # Verify that duration is 0 on command failure
        duration = processor._get_audio_duration(sample_audio_file)
        assert duration == 0
