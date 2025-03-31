import app.models
import os
from dotenv import load_dotenv
from app import create_app

# Load environment variables from .env file
load_dotenv()

# Get application environment from environment variable
env = os.environ.get('FLASK_ENV', 'development')

# Create Flask app (this initializes Celery as well)
flask_app = create_app(env)

# Get Celery app from Flask app
celery = flask_app.celery

# Explicitly import task modules to ensure tasks are registered
import app.tasks.transcription_tasks
import app.tasks.upload_tasks