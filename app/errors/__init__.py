from flask import Blueprint

errors_bp = Blueprint("errors", __name__)
from app.errors import handlers, exceptions


def init_app(app):
    """Initialize error handling for the application."""
    app.register_blueprint(errors_bp)
    from app.errors.handlers import register_handlers

    register_handlers(app)
