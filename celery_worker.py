import os
import app.models
from dotenv import load_dotenv

load_dotenv()

from app import create_app

env = os.environ.get("FLASK_ENV", "development")
flask_app = create_app(env)
celery = flask_app.celery
import app.tasks.transcription_tasks
import app.tasks.upload_tasks
