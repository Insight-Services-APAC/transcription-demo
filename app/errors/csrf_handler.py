import logging
from flask import flash, redirect, url_for, request, jsonify
from flask_wtf.csrf import CSRFError
logger = logging.getLogger('app.errors.csrf')

def register_csrf_handler(app):
    """Register the CSRF error handler with the Flask application."""

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        """Handle CSRF validation errors."""
        logger.warning(f'CSRF validation error: {e.description}. Path: {request.path}')
        if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return (jsonify({'status': 'error', 'error': {'code': 'csrf_error', 'message': 'CSRF validation failed. Please refresh the page and try again.'}}), 400)
        flash('Your form submission could not be processed due to a security validation error. Please try again.', 'danger')
        return redirect(url_for('main.index'))