import pytest
from app import create_app


def test_create_app():
    """Test the create_app function."""
    app = create_app('testing')
    assert app is not None
    assert app.config['TESTING'] is True
    assert app.config['DEBUG'] is True


def test_app_routes(app):
    """Test that all required routes are registered."""
    # Get all routes from the app
    routes = [rule.rule for rule in app.url_map.iter_rules()]

    # Check that all main routes are registered
    assert '/' in routes
    assert '/upload' in routes
    assert '/files' in routes
    assert '/files/<file_id>' in routes
    assert '/transcribe/<file_id>' in routes
    assert '/transcript/<file_id>' in routes
    assert '/api/files' in routes
    assert '/api/transcript/<file_id>' in routes


def test_app_config_values(app):
    """Test that the app has the correct configuration values."""
    assert app.config['UPLOAD_FOLDER'] is not None
    assert app.config['SECRET_KEY'] is not None
    assert app.config['AZURE_STORAGE_CONNECTION_STRING'] is not None
    assert app.config['AZURE_SPEECH_KEY'] is not None
    assert app.config['CELERY_BROKER_URL'] is not None
    assert app.config['CELERY_RESULT_BACKEND'] is not None
    assert app.config['PYANNOTE_AUTH_TOKEN'] is not None
    assert app.config['CHUNK_SIZE_SECONDS'] > 0
    assert app.config['CHUNK_OVERLAP_SECONDS'] > 0
