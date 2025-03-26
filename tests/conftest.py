"""
Pytest fixtures for testing the transcription application.
"""
from app.models import Base
from app import create_app
import os
import sys
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Ensure app directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now we can import from the root module


@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    # Create a temporary file to use as a test database
    db_fd, db_path = tempfile.mkstemp()

    # Create the app with the testing configuration
    app = create_app('testing')

    # Override the database URI to use our temporary database
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"

    # Create all tables in the test database
    with app.app_context():
        from app.models import db_session, engine
        Base.metadata.create_all(engine)

    yield app

    # Close and remove the temporary database
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Create a fresh database session for a test."""
    with app.app_context():
        from app.models import db_session, engine

        # Set up the session for the test
        connection = engine.connect()
        transaction = connection.begin()

        # Configure the session to use this connection
        # This ensures the session doesn't autocommit
        session = db_session
        session.configure(bind=connection)

        yield session

        # Roll back the transaction and close the connection
        transaction.rollback()
        connection.close()

        # Remove the session from the registry
        session.remove()


@pytest.fixture
def mock_azure_blob_service(mocker):
    """Mock the Azure Blob Storage service."""
    mock_blob_service = mocker.patch(
        'app.services.blob_storage.BlobServiceClient')
    mock_blob_client = mocker.MagicMock()
    mock_blob_service.from_connection_string.return_value.get_blob_client.return_value = mock_blob_client
    mock_blob_client.upload_blob.return_value = None
    mock_blob_client.url = "https://example.com/test-blob"
    return mock_blob_service


@pytest.fixture
def mock_speech_service(mocker):
    """Mock the Azure Speech Service."""
    mock_service = mocker.patch('app.services.speech_service.SpeechService')
    mock_service.return_value.transcribe_audio.return_value = {
        "text": "This is a test transcription"}
    return mock_service


@pytest.fixture
def mock_diarization_service(mocker):
    """Mock the speaker diarization service."""
    mock_service = mocker.patch(
        'app.services.diarization_service.DiarizationService')
    mock_service.return_value.diarize.return_value = [
        {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_1"},
        {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_2"}
    ]
    return mock_service


@pytest.fixture
def mock_audio_processor(mocker):
    """Mock the audio processor service."""
    mock_processor = mocker.patch(
        'app.services.audio_processor.AudioProcessor')
    mock_processor.return_value.extract_audio.return_value = "/tmp/test_audio.wav"
    mock_processor.return_value.split_audio.return_value = [
        "/tmp/chunk1.wav", "/tmp/chunk2.wav"]
    return mock_processor


@pytest.fixture
def sample_audio_file():
    """Create a temporary audio file for testing."""
    # Create a temporary WAV file with minimal data
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        # Write minimal WAV header
        f.write(b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00')
        filepath = f.name

    yield filepath

    # Clean up the file after the test
    if os.path.exists(filepath):
        os.unlink(filepath)


@pytest.fixture
def sample_dcr_file():
    """Create a temporary DCR file for testing."""
    # Create a very small binary file to simulate a DCR file
    with tempfile.NamedTemporaryFile(suffix='.dcr', delete=False) as f:
        f.write(b'\x00\x01\x02\x03\x04')
        filepath = f.name

    yield filepath

    # Clean up the file after the test
    if os.path.exists(filepath):
        os.unlink(filepath)
