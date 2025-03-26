import os
import pytest
import tempfile
import shutil
from app import create_app
from app.models import init_db, db_session, engine
from app.models.file import Base, File
import uuid
from datetime import datetime


@pytest.fixture(scope='session')
def app():
    """Create and configure a Flask app for testing."""
    app = create_app('testing')

    # Establish application context
    with app.app_context():
        # Make sure we initialize the database
        init_db(app)

        # Create all tables
        Base.metadata.create_all(bind=engine)

        yield app


@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db(app):
    """Set up a clean database session for a test."""
    from app.models import db_session

    with app.app_context():
        # Start with a clean session for each test
        yield db_session
        # Clean up after the test
        db_session.rollback()


@pytest.fixture(scope='function')
def sample_file(app, db):
    """Create a sample file record."""
    with app.app_context():
        file = File(
            id=str(uuid.uuid4()),
            filename='test_file.dcr',
            upload_time=datetime.utcnow(),
            status='uploaded',
            blob_url='https://example.com/test_file.dcr'
        )
        db.add(file)
        db.commit()

        yield file

        # Clean up
        db.query(File).filter(File.id == file.id).delete()
        db.commit()


@pytest.fixture(scope='function')
def processed_file(app, db):
    """Create a processed file record."""
    with app.app_context():
        file = File(
            id=str(uuid.uuid4()),
            filename='processed_file.dcr',
            upload_time=datetime.utcnow(),
            status='completed',
            blob_url='https://example.com/processed_file.dcr',
            audio_url='https://example.com/processed_file.wav',
            transcript_url='https://example.com/processed_file/transcript/final.json',
            diarization_url='https://example.com/processed_file/diarization/diarization.json',
            speaker_count='3'
        )
        db.add(file)
        db.commit()

        yield file

        # Clean up
        db.query(File).filter(File.id == file.id).delete()
        db.commit()


@pytest.fixture
def mock_services(monkeypatch):
    """Mock all external services for testing."""
    # Mock BlobStorageService
    class MockBlobStorageService:
        def __init__(self, connection_string, container_name):
            self.connection_string = connection_string
            self.container_name = container_name

        def upload_file(self, file_path, blob_path):
            return f"https://example.com/{blob_path}"

        def download_file(self, blob_path, local_path):
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'w') as f:
                f.write('mock content')
            return local_path

    # Mock AudioProcessor
    class MockAudioProcessor:
        def __init__(self, chunk_size_seconds=30, chunk_overlap_seconds=5):
            self.chunk_size_seconds = chunk_size_seconds
            self.chunk_overlap_seconds = chunk_overlap_seconds

        def extract_audio(self, dcr_file_path, output_path=None):
            if output_path is None:
                output_path = os.path.splitext(dcr_file_path)[0] + '.wav'
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                f.write('mock audio content')
            return output_path

        def chunk_audio(self, wav_file_path, output_dir):
            os.makedirs(output_dir, exist_ok=True)
            chunk_paths = []
            for i in range(3):
                chunk_path = os.path.join(output_dir, f"chunk_{i:03d}.wav")
                with open(chunk_path, 'w') as f:
                    f.write(f'mock chunk {i} content')
                chunk_paths.append(chunk_path)
            return chunk_paths

        def _get_smart_boundaries(self, wav_file_path, chunk_size_ms, overlap_ms):
            # Return dummy boundaries that don't require actual wave file reading
            return [(0, 10000), (8000, 18000), (16000, 26000)]

    # Mock SpeechService
    class MockSpeechService:
        def __init__(self, speech_key, speech_region='eastus'):
            self.speech_key = speech_key
            self.speech_region = speech_region

        def transcribe_audio_file(self, audio_file_path, language="en-US"):
            return [
                {
                    'start': '00:00:00',
                    'end': '00:00:10',
                    'text': 'This is a mock transcript.',
                    'words': []
                }
            ]

    # Mock DiarizationService
    class MockDiarizationService:
        def __init__(self, auth_token):
            self.auth_token = auth_token

        def diarize(self, audio_file_path):
            return [
                {
                    'start': '00:00:00',
                    'end': '00:00:10',
                    'speaker': 'Speaker 1'
                }
            ]

        def save_diarization(self, segments, output_file_path):
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            with open(output_file_path, 'w') as f:
                f.write('mock diarization content')
            return output_file_path

    # Mock TranscriptStitcher
    class MockTranscriptStitcher:
        def stitch(self, chunk_transcripts, diarization_segments):
            return [
                {
                    'start': '00:00:00',
                    'end': '00:00:10',
                    'text': 'This is a mock transcript.',
                    'speaker': 'Speaker 1'
                }
            ]

        def save_transcript(self, transcript, json_path, txt_path=None):
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            with open(json_path, 'w') as f:
                f.write('mock transcript content')
            if txt_path:
                os.makedirs(os.path.dirname(txt_path), exist_ok=True)
                with open(txt_path, 'w') as f:
                    f.write('mock transcript text content')
            return json_path, txt_path if txt_path else None

    # Apply the monkeypatches
    from app.services import blob_storage, audio_processor, speech_service, diarization_service, transcript_stitcher

    monkeypatch.setattr(blob_storage, 'BlobStorageService',
                        MockBlobStorageService)
    monkeypatch.setattr(audio_processor, 'AudioProcessor', MockAudioProcessor)
    monkeypatch.setattr(speech_service, 'SpeechService', MockSpeechService)
    monkeypatch.setattr(diarization_service,
                        'DiarizationService', MockDiarizationService)
    monkeypatch.setattr(transcript_stitcher,
                        'TranscriptStitcher', MockTranscriptStitcher)

    return {
        'blob_service': MockBlobStorageService,
        'audio_processor': MockAudioProcessor,
        'speech_service': MockSpeechService,
        'diarization_service': MockDiarizationService,
        'transcript_stitcher': MockTranscriptStitcher
    }


@pytest.fixture(scope='session', autouse=True)
def mock_celery(monkeypatch):
    """Mock celery task execution to run synchronously"""
    def mock_delay(*args, **kwargs):
        from app.tasks.transcription_tasks import transcribe_file as task_func
        return task_func(*args, **kwargs)

    from app.tasks.transcription_tasks import transcribe_file
    monkeypatch.setattr(transcribe_file, 'delay', mock_delay)


@pytest.fixture(scope='session', autouse=True)
def mock_redis(monkeypatch):
    """Mock Redis connection for testing"""
    class MockRedis:
        def __init__(self, *args, **kwargs):
            self.data = {}

        def get(self, key):
            return self.data.get(key)

        def set(self, key, value):
            self.data[key] = value

    # If your code imports Redis directly
    import redis
    monkeypatch.setattr(redis, 'Redis', MockRedis)


@pytest.fixture(scope='session', autouse=True)
def mock_external_services(monkeypatch):
    """Mock external service dependencies"""
    # Mock blob storage service
    class MockBlobStorageService:
        def __init__(self, *args, **kwargs):
            pass

        def upload_file(self, *args, **kwargs):
            return "https://example.com/mock-blob"

        def download_file(self, *args, **kwargs):
            return "/tmp/mock-downloaded-file"

    # Apply mocks
    from app.services import blob_storage
    monkeypatch.setattr(blob_storage, 'BlobStorageService',
                        MockBlobStorageService)

    # Similarly mock other services as needed
