import logging
import json
import traceback
import os
import sys
from datetime import datetime
from flask import has_request_context, request, g, current_app

class JsonFormatter(logging.Formatter):
    """Formatter for structured JSON logs."""

    def format(self, record):
        log_record = {'timestamp': datetime.utcnow().isoformat(), 'level': record.levelname, 'logger': record.name, 'message': super().format(record)}
        if has_request_context():
            log_record.update({'request_id': getattr(g, 'request_id', 'unknown'), 'method': request.method, 'path': request.path, 'ip': request.remote_addr})
        if record.exc_info:
            log_record['exception'] = {'type': record.exc_info[0].__name__, 'message': str(record.exc_info[1]), 'traceback': traceback.format_exception(*record.exc_info)}
        if hasattr(record, 'extra'):
            log_record.update(record.extra)
        return json.dumps(log_record)

def setup_logging(app=None, log_level=None):
    """Configure application logging."""
    if log_level is None:
        log_level = logging.DEBUG if app and app.debug else logging.INFO
    handlers = []
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = JsonFormatter()
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)
    if app and app.config.get('LOG_FILE'):
        log_dir = os.path.dirname(app.config['LOG_FILE'])
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        file_handler = logging.FileHandler(app.config['LOG_FILE'])
        file_formatter = JsonFormatter()
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    for handler in handlers:
        root_logger.addHandler(handler)
    app_logger = logging.getLogger('app')
    app_logger.setLevel(log_level)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    return app_logger

def log_exception(exc, logger=None, level=logging.ERROR, include_traceback=True, extra=None):
    """Log an exception with consistent formatting."""
    if logger is None:
        logger = logging.getLogger('app.errors')
    message = f'Exception: {exc.__class__.__name__}: {str(exc)}'
    if include_traceback:
        tb = traceback.format_exc()
        message += f'\nTraceback:\n{tb}'
    logger.log(level, message, extra=extra)