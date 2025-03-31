import traceback
import logging
from flask import request, jsonify, render_template, flash, redirect, url_for, current_app
from werkzeug.exceptions import HTTPException
from app.errors import errors_bp
from app.errors.exceptions import AppError
logger = logging.getLogger('app.errors')

def is_api_request():
    """Determine if the current request is an API request."""
    return request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

def handle_app_error(error):
    """Handle custom application errors."""
    logger.error(f'{error.error_code}: {error.message}')
    if hasattr(error, 'payload') and error.payload:
        logger.error(f'Additional info: {error.payload}')
    if is_api_request():
        response = error.to_dict()
        response.status_code = error.status_code
        return response
    flash(error.message, 'danger')
    if error.status_code == 404:
        return (render_template('errors/404.html'), 404)
    elif error.status_code in (401, 403):
        return (render_template('errors/403.html'), error.status_code)
    else:
        return (render_template('errors/500.html'), error.status_code)

def handle_http_exception(error):
    """Handle Werkzeug's HTTPExceptions."""
    logger.error(f'HTTP Exception: {error.code} - {error.description}')
    if is_api_request():
        response = {'status': 'error', 'error': {'code': str(error.code), 'message': error.description}}
        response.status_code = error.code
        return response
    flash(error.description, 'danger')
    if error.code == 404:
        return (render_template('errors/404.html'), 404)
    elif error.code in (401, 403):
        return (render_template('errors/403.html'), error.code)
    else:
        return (render_template('errors/500.html'), error.code)

def handle_generic_exception(error):
    """Handle any unhandled exceptions."""
    error_traceback = traceback.format_exc()
    logger.error(f'Unhandled exception: {str(error)}')
    logger.error(error_traceback)
    if is_api_request():
        if current_app.config.get('DEBUG', False):
            msg = str(error)
            detail = error_traceback
        else:
            msg = 'An unexpected error occurred'
            detail = None
        response = {'status': 'error', 'error': {'code': 'server_error', 'message': msg, 'detail': detail}}
        response.status_code = 500
        return response
    flash('An unexpected error occurred', 'danger')
    return (render_template('errors/500.html'), 500)

def register_handlers(app):
    """Register error handlers with the Flask application."""
    app.register_error_handler(AppError, handle_app_error)
    app.register_error_handler(HTTPException, handle_http_exception)
    app.register_error_handler(404, handle_http_exception)
    app.register_error_handler(500, handle_generic_exception)
    app.register_error_handler(Exception, handle_generic_exception)

@errors_bp.route('/404')
def page_not_found():
    return (render_template('errors/404.html'), 404)

@errors_bp.route('/403')
def forbidden():
    return (render_template('errors/403.html'), 403)

@errors_bp.route('/500')
def server_error():
    return (render_template('errors/500.html'), 500)