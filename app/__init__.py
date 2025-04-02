import os
from flask import Flask
from config import config
from app.extensions import db, csrf, login_manager
from app.tasks.celery_app import make_celery
from flask_migrate import Migrate

def create_app(config_name='default'):
    app = Flask(__name__, instance_relative_config=True)
    app_config = config[config_name]
    app.config.from_object(app_config)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.instance_path, exist_ok=True)
    from app.errors.logger import setup_logging
    setup_logging(app)
    db.init_app(app)
    csrf.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(user_id)
    from app.errors import init_app as init_errors
    init_errors(app)
    from app.errors.middleware import init_middleware
    init_middleware(app)
    
    # Initialize password change middleware
    from app.auth.middleware import init_password_middleware
    init_password_middleware(app)
    
    # Import all blueprints
    from app.main import main_bp
    from app.files import files_bp
    from app.transcripts import transcripts_bp
    from app.auth import auth_bp
    from app.admin import admin_bp
    
    # Register all blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(transcripts_bp)
    app.register_blueprint(auth_bp) 
    app.register_blueprint(admin_bp)
    
    app.celery = make_celery(app)
    from app.errors.csrf_handler import register_csrf_handler
    register_csrf_handler(app)
    return app