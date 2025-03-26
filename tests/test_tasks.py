import pytest
import os
import tempfile
import shutil
from app.models.file import File
from app.tasks.transcription_tasks import (
    transcribe_file, extract_audio, chunk_audio,
    transcribe_chunks, perform_diarization, stitch_transcript
)


def test_transcribe_file(app, sample_file, db, monkeypatch):
    """Test the main transcription task."""
    with app.app_context():
        # Mock the chain task
        class MockChain:
            def __init__(self, *tasks):
                self.tasks = tasks

            def apply_async(self):
                return MockAsyncResult()

        class MockAsyncResult:
            id = "mock-task-id"

        def mock_chain(*args, **kwargs):
            return MockChain(*args)

        # Mock db_session in the task
        monkeypatch.setattr('app.tasks.transcription_tasks.db_session', db)

        # Apply the monkeypatch
        from celery import chain
        monkeypatch.setattr('celery.chain', mock_chain)

        # Call the task
        result = transcribe_file(sample_file.id)

        # Check the result
        assert result["status"] == "success"
        assert "task_id" in result

        # Check that the file status was updated
        updated_file = db.query(File).filter(File.id == sample_file.id).first()
        assert updated_file.status == "processing"


def test_transcribe_file_not_found(app, db, monkeypatch):
    """Test handling a non-existent file ID."""
    with app.app_context():
        # Mock db_session in the task
        monkeypatch.setattr('app.tasks.transcription_tasks.db_session', db)

        result = transcribe_file("non-existent-id")
        assert result["status"] == "error"
        assert "not found" in result["message"]


def test_extract_audio(app, sample_file, mock_services, monkeypatch, tmp_path, db):
    """Test the extract_audio task."""
    with app.app_context():
        # Mock get_blob_service and get_audio_processor
        def mock_get_blob_service():
            return mock_services['blob_service']('mock-connection-string', 'test-container')

        def mock_get_audio_processor():
            return mock_services['audio_processor'](chunk_size_seconds=30, chunk_overlap_seconds=5)

        # Mock db_session in the task
        monkeypatch.setattr('app.tasks.transcription_tasks.db_session', db)

        # Apply the monkeypatches
        from app.tasks import transcription_tasks
        monkeypatch.setattr(transcription_tasks,
                            'get_blob_service', mock_get_blob_service)
        monkeypatch.setattr(transcription_tasks,
                            'get_audio_processor', mock_get_audio_processor)

        # Mock tempfile.mkdtemp to return a controlled directory
        temp_dir = str(tmp_path / "temp")
        os.makedirs(temp_dir, exist_ok=True)
        monkeypatch.setattr(tempfile, 'mkdtemp', lambda: temp_dir)

        # Call the task
        result = extract_audio(sample_file.id)

        # Check the result
        assert "audio_path" in result
        assert "audio_blob_path" in result
        assert "temp_dir" in result
        assert result["temp_dir"] == temp_dir

        # Check that the file audio_url was updated
        updated_file = db.query(File).filter(File.id == sample_file.id).first()
        assert updated_file.audio_url is not None


def test_chunk_audio(app, mock_services, monkeypatch, tmp_path):
    """Test the chunk_audio task."""
    # Create a test directory with an audio file
    temp_dir = str(tmp_path / "temp")
    os.makedirs(temp_dir, exist_ok=True)
    audio_path = os.path.join(temp_dir, "test.wav")

    # Create a mock WAV file with RIFF header
    with open(audio_path, 'wb') as f:
        # Write a basic RIFF header for a WAV file
        f.write(b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xAC\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00')

    # Mock get_audio_processor
    def mock_get_audio_processor():
        return mock_services['audio_processor'](chunk_size_seconds=30, chunk_overlap_seconds=5)

    # Apply the monkeypatch
    from app.tasks import transcription_tasks
    monkeypatch.setattr(transcription_tasks,
                        'get_audio_processor', mock_get_audio_processor)

    # Create input for the task
    previous_result = {
        "audio_path": audio_path,
        "audio_blob_path": "test.wav",
        "temp_dir": temp_dir
    }

    # Call the task
    result = chunk_audio(previous_result)

    # Check the result
    assert "chunk_paths" in result
    assert len(result["chunk_paths"]) > 0
    assert "chunks_dir" in result
    assert os.path.exists(result["chunks_dir"])


def test_transcribe_chunks(app, sample_file, mock_services, monkeypatch, tmp_path, db):
    """Test the transcribe_chunks task."""
    with app.app_context():
        # Create a test directory with chunk files
        temp_dir = str(tmp_path / "temp")
        chunks_dir = os.path.join(temp_dir, "chunks")
        os.makedirs(chunks_dir, exist_ok=True)

        chunk_paths = []
        for i in range(3):
            chunk_path = os.path.join(chunks_dir, f"chunk_{i:03d}.wav")
            with open(chunk_path, 'w') as f:
                f.write(f"mock chunk {i} content")
            chunk_paths.append(chunk_path)

        # Mock get_speech_service
        def mock_get_speech_service():
            return mock_services['speech_service']('mock-speech-key', 'eastus')

        # Mock db_session in the task
        monkeypatch.setattr('app.tasks.transcription_tasks.db_session', db)

        # Apply the monkeypatch
        from app.tasks import transcription_tasks
        monkeypatch.setattr(transcription_tasks,
                            'get_speech_service', mock_get_speech_service)

        # Create input for the task
        previous_result = {
            "audio_path": os.path.join(temp_dir, "test.wav"),
            "audio_blob_path": "test.wav",
            "temp_dir": temp_dir,
            "chunk_paths": chunk_paths,
            "chunks_dir": chunks_dir
        }

        # Call the task
        result = transcribe_chunks(previous_result, sample_file.id)

        # Check the result
        assert "chunk_transcripts" in result
        assert len(result["chunk_transcripts"]) == 3
        assert "transcripts_dir" in result
        assert os.path.exists(result["transcripts_dir"])

        # Check that transcript files were created
        for i in range(3):
            transcript_path = os.path.join(
                result["transcripts_dir"], f"chunk_{i:03d}.json")
            assert os.path.exists(transcript_path)


def test_perform_diarization(app, sample_file, mock_services, monkeypatch, tmp_path, db):
    """Test the perform_diarization task."""
    with app.app_context():
        # Create a test directory with an audio file
        temp_dir = str(tmp_path / "temp")
        os.makedirs(temp_dir, exist_ok=True)
        audio_path = os.path.join(temp_dir, "test.wav")
        with open(audio_path, 'w') as f:
            f.write("mock audio content")

        # Mock service functions
        def mock_get_diarization_service():
            return mock_services['diarization_service']('mock-auth-token')

        def mock_get_blob_service():
            return mock_services['blob_service']('mock-connection-string', 'test-container')

        # Mock db_session in the task
        monkeypatch.setattr('app.tasks.transcription_tasks.db_session', db)

        # Apply the monkeypatches
        from app.tasks import transcription_tasks
        monkeypatch.setattr(
            transcription_tasks, 'get_diarization_service', mock_get_diarization_service)
        monkeypatch.setattr(transcription_tasks,
                            'get_blob_service', mock_get_blob_service)

        # Create input for the task
        previous_result = {
            "audio_path": audio_path,
            "audio_blob_path": "test.wav",
            "temp_dir": temp_dir,
            "chunk_paths": [os.path.join(temp_dir, "chunk_000.wav")],
            "chunks_dir": os.path.join(temp_dir, "chunks")
        }

        # Call the task
        result = perform_diarization(previous_result, sample_file.id)

        # Check the result
        assert "diarization_segments" in result
        assert len(result["diarization_segments"]) > 0
        assert "diarization_path" in result
        assert os.path.exists(result["diarization_path"])

        # Check that the file was updated
        updated_file = db.query(File).filter(File.id == sample_file.id).first()
        assert updated_file.diarization_url is not None
        assert updated_file.speaker_count is not None


def test_stitch_transcript(app, sample_file, mock_services, monkeypatch, tmp_path, db):
    """Test the stitch_transcript task."""
    with app.app_context():
        # Create a test directory
        temp_dir = str(tmp_path / "temp")
        os.makedirs(temp_dir, exist_ok=True)

        # Mock service functions
        def mock_get_transcript_stitcher():
            return mock_services['transcript_stitcher']()

        def mock_get_blob_service():
            return mock_services['blob_service']('mock-connection-string', 'test-container')

        # Mock db_session in the task
        monkeypatch.setattr('app.tasks.transcription_tasks.db_session', db)

        # Apply the monkeypatches
        from app.tasks import transcription_tasks
        monkeypatch.setattr(
            transcription_tasks, 'get_transcript_stitcher', mock_get_transcript_stitcher)
        monkeypatch.setattr(transcription_tasks,
                            'get_blob_service', mock_get_blob_service)

        # Create mock diarization segments
        diarization_segments = [
            {
                'start': '00:00:00',
                'end': '00:00:10',
                'speaker': 'Speaker 1'
            }
        ]

        # Create mock chunk transcripts
        chunk_transcripts = [
            [
                {
                    'start': '00:00:00',
                    'end': '00:00:10',
                    'text': 'This is a test transcript.'
                }
            ]
        ]

        # Create input for the task
        previous_result = {
            "audio_path": os.path.join(temp_dir, "test.wav"),
            "audio_blob_path": "test.wav",
            "temp_dir": temp_dir,
            "chunk_transcripts": chunk_transcripts,
            "diarization_segments": diarization_segments
        }

        # Call the task
        result = stitch_transcript(previous_result, sample_file.id)

        # Check the result
        assert result["status"] == "success"
        assert "transcript_url" in result

        # Check that the file was updated
        updated_file = db.query(File).filter(File.id == sample_file.id).first()
        assert updated_file.transcript_url is not None
        assert updated_file.status == "completed"
