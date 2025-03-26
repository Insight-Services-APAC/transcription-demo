import os
import pytest
import tempfile
import shutil
from app import create_app
import uuid
from datetime import datetime
from unittest import mock
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base


@pytest.fixture(scope='session')
def app():
    """Create and configure a Flask app for testing."""
    # Create the Flask app with testing config
    flask_app = create_app('testing')

    # Establish application context
    with flask_app.app_context():
        # Initialize database explicitly
        from app.models.file import Base

        # Create an in-memory SQLite database for testing
        engine = create_engine('sqlite:///:memory:')
        db_session = scoped_session(sessionmaker(
            autocommit=False, autoflush=False, bind=engine))
        Base.query = db_session.query_property()

        # Import models to ensure they're registered with the metadata
        from app.models.file import File

        # Create all tables
        Base.metadata.create_all(bind=engine)

        # Make the session and engine available to the app
        flask_app.db_session = db_session
        flask_app.engine = engine

        # Replace the existing db_session in app.models
        import app.models
        app.models.db_session = db_session
        app.models.engine = engine

        # Add a teardown to clean up the session
        @flask_app.teardown_appcontext
        def shutdown_session(exception=None):
            db_session.remove()

        yield flask_app


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
    with app.app_context():
        # Use the session from the app
        db_session = app.db_session
        db_session.begin_nested()  # Create a savepoint

        yield db_session

        # Clean up after the test
        db_session.rollback()


@pytest.fixture(scope='function')
def sample_file(app, db):
    """Create a sample file record."""
    with app.app_context():
        from app.models.file import File

        file_id = str(uuid.uuid4())
        file = File(
            id=file_id,
            filename='test_file.dcr',
            upload_time=datetime.utcnow(),
            status='uploaded',
            blob_url='https://example.com/test_file.dcr'
        )
        db.add(file)
        db.commit()

        # Store the ID for safe cleanup
        yield file

        # Clean up safely - don't rely on the file object which might be detached
        try:
            db.execute(f"DELETE FROM files WHERE id = '{file_id}'")
            db.commit()
        except Exception:
            db.rollback()


@pytest.fixture(scope='function')
def processed_file(app, db):
    """Create a processed file record."""
    with app.app_context():
        from app.models.file import File

        file_id = str(uuid.uuid4())
        file = File(
            id=file_id,
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

        # Store the ID for safe cleanup
        yield file

        # Clean up safely - don't rely on the file object which might be detached
        try:
            db.execute(f"DELETE FROM files WHERE id = '{file_id}'")
            db.commit()
        except Exception:
            db.rollback()


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


# Simplified mock_celery fixture that doesn't use patching
@pytest.fixture(scope='session', autouse=True)
def mock_celery():
    """Mock celery task execution to run synchronously"""
    # Mock the delay method of transcribe_file
    from app.tasks.transcription_tasks import transcribe_file

    # Store original method if it exists
    original_delay = getattr(transcribe_file, 'delay', None)

    # Create a simpler mock that doesn't rely on patching
    def mock_delay(*args, **kwargs):
        return transcribe_file(*args, **kwargs)

    # Directly replace the method
    transcribe_file.delay = mock_delay

    yield

    # Try to restore if needed, but don't fail if it's not possible
    if original_delay:
        try:
            transcribe_file.delay = original_delay
        except Exception:
            pass


# Fixed: Use direct attribute setting instead of context manager
@pytest.fixture(scope='session', autouse=True)
def mock_redis():
    """Mock Redis connection for testing"""
    class MockRedis:
        def __init__(self, *args, **kwargs):
            self.data = {}

        def get(self, key):
            return self.data.get(key)

        def set(self, key, value):
            self.data[key] = value

    # Use direct patching
    import redis
    original_redis = redis.Redis
    redis.Redis = MockRedis

    yield

    # Restore original
    redis.Redis = original_redis


# Fixed: Use direct attribute setting instead of context manager
@pytest.fixture(scope='session', autouse=True)
def mock_external_services():
    """Mock external service dependencies"""
    # Mock blob storage service
    class MockBlobStorageService:
        def __init__(self, *args, **kwargs):
            pass

        def upload_file(self, *args, **kwargs):
            return "https://example.com/mock-blob"

        def download_file(self, *args, **kwargs):
            return "/tmp/mock-downloaded-file"

    # Apply direct patching
    from app.services import blob_storage
    original_service = blob_storage.BlobStorageService
    blob_storage.BlobStorageService = MockBlobStorageService

    yield

    # Restore
    blob_storage.BlobStorageService = original_service


# Set mock environment variables for testing
@pytest.fixture(scope='session', autouse=True)
def mock_env_vars():
    """Set mock environment variables for testing."""
    os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'mock-connection-string'
    os.environ['AZURE_SPEECH_KEY'] = 'mock-speech-key'
    os.environ['PYANNOTE_AUTH_TOKEN'] = 'mock-auth-token'

    yield

    # Clean up after tests
    os.environ.pop('AZURE_STORAGE_CONNECTION_STRING', None)
    os.environ.pop('AZURE_SPEECH_KEY', None)
    os.environ.pop('PYANNOTE_AUTH_TOKEN', None)
