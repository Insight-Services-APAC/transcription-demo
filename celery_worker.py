from app.models import init_db
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

# Ensure database session is initialized
# This explicit import is important to initialize models
init_db(flask_app)
