import os
from flask import Flask
from app.models import init_db
from app.tasks.celery_app import make_celery
from config import config

# Initialize Flask app
def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load configuration
    app_config = config[config_name]
    app.config.from_object(app_config)
    
    # Create uploads directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize database
    init_db(app)
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.files import files_bp
    from app.routes.transcripts import transcripts_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(transcripts_bp)
    
    # Initialize Celery
    app.celery = make_celery(app)
    
    return app