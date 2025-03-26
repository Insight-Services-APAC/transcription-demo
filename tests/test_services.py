import pytest
import os
import tempfile
import shutil
import json
from app.services.blob_storage import BlobStorageService
from app.services.audio_processor import AudioProcessor
from app.services.speech_service import SpeechService
from app.services.diarization_service import DiarizationService
from app.services.transcript_stitcher import TranscriptStitcher


class TestBlobStorageService:
    """Tests for the BlobStorageService class."""

    @pytest.fixture
    def blob_service(self, monkeypatch):
        """Create a BlobStorageService instance with mocked Azure SDK."""
        # Mock the BlobServiceClient
        class MockBlobServiceClient:
            def __init__(self, conn_str):
                self.conn_str = conn_str

            def get_blob_client(self, container, blob):
                return MockBlobClient(container, blob)

            def create_container(self, name):
                return None

        # Mock the BlobClient
        class MockBlobClient:
            def __init__(self, container, blob):
                self.container = container
                self.blob = blob
                self.url = f"https://example.com/{container}/{blob}"

            def upload_blob(self, data, overwrite=False, content_settings=None):
                return None

            def download_blob(self):
                return MockDownloadedBlob()

        # Mock the DownloadedBlob
        class MockDownloadedBlob:
            def readall(self):
                return b'mock blob content'

        # Mock the ContentSettings
        class MockContentSettings:
            def __init__(self, content_type=None):
                self.content_type = content_type

        # Apply the monkeypatches
        from azure.storage.blob import BlobServiceClient, ContentSettings
        monkeypatch.setattr('azure.storage.blob.BlobServiceClient.from_connection_string',
                            lambda conn_str: MockBlobServiceClient(conn_str))
        monkeypatch.setattr(
            'azure.storage.blob.ContentSettings', MockContentSettings)

        # Create and return the service
        return BlobStorageService('mock-connection-string', 'test-container')

    def test_upload_file(self, blob_service, tmp_path):
        """Test uploading a file to blob storage."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        # Upload the file
        url = blob_service.upload_file(str(test_file), "test.txt")

        # Check the result
        assert url == "https://example.com/test-container/test.txt"

    def test_download_file(self, blob_service, tmp_path):
        """Test downloading a file from blob storage."""
        # Define the output path
        output_path = str(tmp_path / "downloaded.txt")

        # Download the file
        result = blob_service.download_file("test.txt", output_path)

        # Check the result
        assert result == output_path
        assert os.path.exists(output_path)
        with open(output_path, 'rb') as f:
            content = f.read()
            assert content == b'mock blob content'

    def test_get_blob_url(self, blob_service):
        """Test getting the URL for a blob."""
        url = blob_service.get_blob_url("test.txt")
        assert url == "https://example.com/test-container/test.txt"


class TestAudioProcessor:
    """Tests for the AudioProcessor class."""

    @pytest.fixture
    def audio_processor(self, monkeypatch):
        """Create an AudioProcessor instance with mocked dependencies."""
        # Mock the ffmpeg module
        class MockFFmpeg:
            @staticmethod
            def input(input_path):
                return MockFFmpegInput(input_path)

        class MockFFmpegInput:
            def __init__(self, input_path):
                self.input_path = input_path

            def output(self, output_path, acodec=None, vn=None):
                return MockFFmpegOutput(self.input_path, output_path)

        class MockFFmpegOutput:
            def __init__(self, input_path, output_path):
                self.input_path = input_path
                self.output_path = output_path

            def run(self, quiet=False, overwrite_output=False):
                # Create a mock WAV file
                with open(self.output_path, 'w') as f:
                    f.write("mock wav content")
                return None

        # Mock the AudioSegment
        class MockAudioSegment:
            @staticmethod
            def from_wav(wav_path):
                return MockAudioSegment()

            def __len__(self):
                return 60000  # 60 seconds in milliseconds

            def __getitem__(self, slice_obj):
                return MockAudioSegment()

            def export(self, output_path, format):
                with open(output_path, 'w') as f:
                    f.write(f"mock chunk content for {output_path}")
                return None

        # Apply the monkeypatches
        import ffmpeg
        import pydub
        monkeypatch.setattr(ffmpeg, 'input', MockFFmpeg.input)
        monkeypatch.setattr(pydub.AudioSegment, 'from_wav',
                            MockAudioSegment.from_wav)

        # Override the _get_smart_boundaries method
        def mock_get_smart_boundaries(self, wav_file_path, chunk_size_ms, overlap_ms):
            return [(0, 10000), (8000, 18000), (16000, 26000)]

        monkeypatch.setattr(
            AudioProcessor, '_get_smart_boundaries', mock_get_smart_boundaries)

        # Create and return the processor
        return AudioProcessor(chunk_size_seconds=10, chunk_overlap_seconds=2)

    def test_extract_audio(self, audio_processor, tmp_path):
        """Test extracting audio from a DCR file."""
        # Create a test DCR file
        dcr_path = tmp_path / "test.dcr"
        dcr_path.write_text("mock dcr content")

        # Extract audio
        wav_path = audio_processor.extract_audio(str(dcr_path))

        # Check the result
        assert wav_path == str(tmp_path / "test.wav")
        assert os.path.exists(wav_path)
        with open(wav_path, 'r') as f:
            content = f.read()
            assert content == "mock wav content"

    def test_chunk_audio(self, audio_processor, tmp_path):
        """Test chunking an audio file."""
        # Create a test WAV file
        wav_path = tmp_path / "test.wav"
        wav_path.write_text("mock wav content")

        # Create output directory
        output_dir = tmp_path / "chunks"
        os.makedirs(output_dir, exist_ok=True)

        # Chunk the audio - will use our mocked _get_smart_boundaries
        chunk_paths = audio_processor.chunk_audio(
            str(wav_path), str(output_dir))

        # Should have chunks
        assert len(chunk_paths) > 0
        for path in chunk_paths:
            assert os.path.exists(path)
            assert path.startswith(str(output_dir))


class TestTranscriptStitcher:
    """Tests for the TranscriptStitcher class."""

    @pytest.fixture
    def transcript_stitcher(self):
        """Create a TranscriptStitcher instance."""
        return TranscriptStitcher()

    def test_stitch(self, transcript_stitcher):
        """Test stitching transcripts with diarization."""
        # Create test data
        chunk_transcripts = [
            [
                {
                    'start': '00:00:00',
                    'end': '00:00:10',
                    'text': 'This is the first segment.'
                }
            ],
            [
                {
                    'start': '00:00:08',
                    'end': '00:00:15',
                    'text': 'This is the second segment.'
                }
            ]
        ]

        diarization_segments = [
            {
                'start': '00:00:00',
                'end': '00:00:12',
                'speaker': 'Speaker 1'
            },
            {
                'start': '00:00:12',
                'end': '00:00:20',
                'speaker': 'Speaker 2'
            }
        ]

        # Stitch the transcript
        result = transcript_stitcher.stitch(
            chunk_transcripts, diarization_segments)

        # Check the result
        assert isinstance(result, list)
        assert len(result) > 0

        # Check that all segments have speaker labels
        for segment in result:
            assert 'speaker' in segment
            assert segment['speaker'] in ['Speaker 1', 'Speaker 2', 'Unknown']

    def test_save_transcript(self, transcript_stitcher, tmp_path):
        """Test saving transcript to files."""
        # Create test data
        transcript = [
            {
                'start': '00:00:00',
                'end': '00:00:10',
                'text': 'This is a test transcript.',
                'speaker': 'Speaker 1'
            }
        ]

        # Define output paths
        json_path = str(tmp_path / "transcript.json")
        txt_path = str(tmp_path / "transcript.txt")

        # Save the transcript
        result_json, result_txt = transcript_stitcher.save_transcript(
            transcript, json_path, txt_path)

        # Check the result
        assert result_json == json_path
        assert result_txt == txt_path

        # Check that the files exist
        assert os.path.exists(json_path)
        assert os.path.exists(txt_path)

        # Check the content
        with open(json_path, 'r') as f:
            json_content = json.load(f)
            assert isinstance(json_content, list)
            assert len(json_content) == 1

        with open(txt_path, 'r') as f:
            txt_content = f.read()
            assert "Speaker 1" in txt_content
            assert "This is a test transcript." in txt_content
