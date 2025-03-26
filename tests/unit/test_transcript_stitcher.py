"""
Unit tests for the TranscriptStitcher class.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.transcript_stitcher import TranscriptStitcher


class TestTranscriptStitcher:
    """Tests for the TranscriptStitcher class."""

    @pytest.fixture
    def transcript_data(self):
        """Sample transcript data for testing."""
        return [
            {"text": "Hello, this is speaker one."},
            {"text": "This is still speaker one continuing."},
            {"text": "Now this is speaker two."}
        ]

    @pytest.fixture
    def diarization_data(self):
        """Sample diarization data for testing."""
        return [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
            {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_00"},
            {"start": 10.0, "end": 15.0, "speaker": "SPEAKER_01"}
        ]

    @pytest.fixture
    def stitcher(self):
        """Create a TranscriptStitcher instance."""
        return TranscriptStitcher()

    def test_initialization(self, stitcher):
        """Test that TranscriptStitcher initializes correctly."""
        assert hasattr(stitcher, 'stitch_transcript')

    def test_stitch_transcript(self, stitcher, transcript_data, diarization_data):
        """Test stitching transcript with diarization data."""
        # Call the method
        result = stitcher.stitch_transcript(transcript_data, diarization_data)

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 3

        # Check first segment
        assert result[0]["text"] == "Hello, this is speaker one."
        assert result[0]["speaker"] == "SPEAKER_00"
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 5.0

        # Check second segment
        assert result[1]["text"] == "This is still speaker one continuing."
        assert result[1]["speaker"] == "SPEAKER_00"
        assert result[1]["start"] == 5.0
        assert result[1]["end"] == 10.0

        # Check third segment
        assert result[2]["text"] == "Now this is speaker two."
        assert result[2]["speaker"] == "SPEAKER_01"
        assert result[2]["start"] == 10.0
        assert result[2]["end"] == 15.0

    def test_stitch_transcript_mismatched_lengths(self, stitcher, transcript_data):
        """Test handling of mismatched transcript and diarization data."""
        # Create mismatched diarization data (fewer segments than transcript)
        diarization_data = [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
            {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_01"}
        ]

        # Call the method
        result = stitcher.stitch_transcript(transcript_data, diarization_data)

        # Verify the result
        assert isinstance(result, list)
        # Only two segments due to diarization data limit
        assert len(result) == 2

        # Check first segment
        assert result[0]["text"] == "Hello, this is speaker one."
        assert result[0]["speaker"] == "SPEAKER_00"

        # Check second segment
        assert result[1]["text"] == "This is still speaker one continuing."
        assert result[1]["speaker"] == "SPEAKER_01"

    def test_stitch_transcript_empty_data(self, stitcher):
        """Test stitching with empty data."""
        # Call with empty data
        result = stitcher.stitch_transcript([], [])

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 0

    def test_format_transcript(self, stitcher, transcript_data, diarization_data):
        """Test formatting the transcript into text format."""
        # Stitch the transcript first
        stitched = stitcher.stitch_transcript(
            transcript_data, diarization_data)

        # Format the transcript
        formatted = stitcher.format_transcript(stitched)

        # Verify the result
        assert isinstance(formatted, str)
        assert "SPEAKER_00" in formatted
        assert "SPEAKER_01" in formatted
        assert "Hello, this is speaker one." in formatted
        assert "Now this is speaker two." in formatted

    def test_format_transcript_empty(self, stitcher):
        """Test formatting empty transcript."""
        # Call with empty data
        formatted = stitcher.format_transcript([])

        # Verify the result
        assert isinstance(formatted, str)
        assert formatted == ""  # Empty string is expected for empty transcript

    def test_merge_consecutive_speaker_segments(self, stitcher):
        """Test merging consecutive segments from the same speaker."""
        # Create sample data with consecutive segments from the same speaker
        stitched_data = [
            {"text": "Hello, this is speaker one.",
                "speaker": "SPEAKER_00", "start": 0.0, "end": 5.0},
            {"text": "Still speaker one.", "speaker": "SPEAKER_00",
                "start": 5.0, "end": 10.0},
            {"text": "Now speaker two.", "speaker": "SPEAKER_01",
                "start": 10.0, "end": 15.0},
            {"text": "Still speaker two.", "speaker": "SPEAKER_01",
                "start": 15.0, "end": 20.0},
            {"text": "Back to speaker one.",
                "speaker": "SPEAKER_00", "start": 20.0, "end": 25.0}
        ]

        # Merge the segments
        merged = stitcher.merge_consecutive_speaker_segments(stitched_data)

        # Verify the result
        assert isinstance(merged, list)
        assert len(merged) == 3  # Should merge into 3 segments

        # Check first segment (merged SPEAKER_00)
        assert merged[0]["speaker"] == "SPEAKER_00"
        assert "Hello, this is speaker one. Still speaker one." in merged[0]["text"]
        assert merged[0]["start"] == 0.0
        assert merged[0]["end"] == 10.0

        # Check second segment (merged SPEAKER_01)
        assert merged[1]["speaker"] == "SPEAKER_01"
        assert "Now speaker two. Still speaker two." in merged[1]["text"]
        assert merged[1]["start"] == 10.0
        assert merged[1]["end"] == 20.0

        # Check third segment (single SPEAKER_00)
        assert merged[2]["speaker"] == "SPEAKER_00"
        assert merged[2]["text"] == "Back to speaker one."
        assert merged[2]["start"] == 20.0
        assert merged[2]["end"] == 25.0
