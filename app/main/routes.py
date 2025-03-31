from flask import redirect, url_for
from app.main import main_bp
from app.extensions import csrf

@main_bp.route('/')
def index():
    """Redirect to upload page"""
    return redirect(url_for('files.upload'))

@main_bp.route('/health')
@csrf.exempt  # Exempt health check endpoint from CSRF protection
def health():
    """Health check endpoint"""
    return {'status': 'ok'}