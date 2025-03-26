"""
Unit tests for the DiarizationService class.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from app.services.diarization_service import DiarizationService


class TestDiarizationService:
    """Tests for the DiarizationService class."""

    @pytest.fixture
    def diarization_service(self):
        """Create a DiarizationService instance with mocked dependencies."""
        with patch('app.services.diarization_service.torch') as mock_torch:
            with patch('app.services.diarization_service.Pipeline') as mock_pipeline:
                # Configure the mock
                mock_torch.cuda.is_available.return_value = False
                mock_pipeline.from_pretrained.return_value = MagicMock()

                # Mock diarization result
                mock_result = MagicMock()
                mock_result.for_json.return_value = {
                    'content': [
                        {'segment': {'start': 0.0, 'end': 5.0},
                            'track': 'SPEAKER_00'},
                        {'segment': {'start': 5.0, 'end': 10.0},
                            'track': 'SPEAKER_01'}
                    ]
                }
                mock_pipeline.from_pretrained.return_value.return_value = mock_result

                service = DiarizationService(use_gpu=False)
                yield service

    def test_initialization(self, diarization_service):
        """Test that DiarizationService initializes correctly."""
        assert hasattr(diarization_service, 'pipeline')
        assert diarization_service.use_gpu is False

    @patch('os.path.exists')
    def test_diarize(self, mock_exists, diarization_service, sample_audio_file):
        """Test diarizing an audio file."""
        # Setup
        mock_exists.return_value = True

        # Call the method
        result = diarization_service.diarize(sample_audio_file)

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 2

        # Check first segment
        assert result[0]['start'] == 0.0
        assert result[0]['end'] == 5.0
        assert result[0]['speaker'] == 'SPEAKER_00'

        # Check second segment
        assert result[1]['start'] == 5.0
        assert result[1]['end'] == 10.0
        assert result[1]['speaker'] == 'SPEAKER_01'

    @patch('os.path.exists')
    def test_diarize_file_not_found(self, mock_exists, diarization_service):
        """Test handling of file not found error."""
        # Setup
        mock_exists.return_value = False

        # Verify exception is raised
        with pytest.raises(FileNotFoundError):
            diarization_service.diarize("nonexistent_file.wav")

    @patch('os.path.exists')
    def test_diarize_pipeline_error(self, mock_exists, diarization_service, sample_audio_file):
        """Test handling of pipeline errors."""
        # Setup
        mock_exists.return_value = True

        # Mock a pipeline error
        diarization_service.pipeline.side_effect = Exception("Pipeline Error")

        # Verify exception is raised and properly formatted
        with pytest.raises(Exception):
            diarization_service.diarize(sample_audio_file)

    @patch('os.path.exists')
    @patch('app.services.diarization_service.torch')
    def test_gpu_initialization(self, mock_torch, mock_exists, sample_audio_file):
        """Test initialization with GPU when available."""
        # Setup
        mock_exists.return_value = True
        mock_torch.cuda.is_available.return_value = True

        with patch('app.services.diarization_service.Pipeline') as mock_pipeline:
            # Configure the mock
            mock_pipeline.from_pretrained.return_value = MagicMock()

            # Mock diarization result
            mock_result = MagicMock()
            mock_result.for_json.return_value = {
                'content': [
                    {'segment': {'start': 0.0, 'end': 5.0}, 'track': 'SPEAKER_00'}
                ]
            }
            mock_pipeline.from_pretrained.return_value.return_value = mock_result

            # Create service with GPU enabled
            service = DiarizationService(use_gpu=True)

            # Verify GPU is used
            assert service.use_gpu is True

            # Call the method
            result = service.diarize(sample_audio_file)

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 1
