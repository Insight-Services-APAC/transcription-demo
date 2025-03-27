# app/__init__.py
import os
from flask import Flask
from config import config
from app.extensions import db
from app.tasks.celery_app import make_celery
from flask_migrate import Migrate

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load configuration
    app_config = config[config_name]
    app.config.from_object(app_config)
    
    # Create uploads directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)
    
    # Register blueprints
    from app.main import main_bp
    from app.files import files_bp
    from app.transcripts import transcripts_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(transcripts_bp)
    
    # Initialize Celery
    app.celery = make_celery(app)
    
    return app
