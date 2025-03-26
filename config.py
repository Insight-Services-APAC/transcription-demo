import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-for-demo')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///instance/app.db')
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024 * 1024  # 5GB max for .DCR files

    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING = os.environ.get(
        'AZURE_STORAGE_CONNECTION_STRING')
    AZURE_STORAGE_CONTAINER = os.environ.get(
        'AZURE_STORAGE_CONTAINER', 'transcriptions')

    # Azure Speech Services
    AZURE_SPEECH_KEY = os.environ.get('AZURE_SPEECH_KEY')
    AZURE_SPEECH_REGION = os.environ.get('AZURE_SPEECH_REGION', 'eastus')

    # Celery Configuration
    broker_url = os.environ.get(
        'CELERY_BROKER_URL', 'redis://localhost:6379/0')
    result_backend = os.environ.get(
        'CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    # Keep old keys for backward compatibility (will be removed in future)
    CELERY_BROKER_URL = broker_url
    CELERY_RESULT_BACKEND = result_backend
    broker_connection_retry_on_startup = True

    # Audio Processing
    CHUNK_SIZE_SECONDS = int(os.environ.get('CHUNK_SIZE_SECONDS', 30))
    CHUNK_OVERLAP_SECONDS = int(os.environ.get('CHUNK_OVERLAP_SECONDS', 5))

    # PyAnnote Configuration
    PYANNOTE_AUTH_TOKEN = os.environ.get('PYANNOTE_AUTH_TOKEN')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost.localdomain'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
