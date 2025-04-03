from flask import redirect, url_for
from flask_login import login_required
from app.main import main_bp
from app.extensions import csrf
from app.auth.decorators import approval_required
import logging

logger = logging.getLogger(__name__)


@main_bp.route("/")
@approval_required
def index():
    """Redirect to upload page"""
    return redirect(url_for("files.upload"))


@main_bp.route("/health")
@csrf.exempt
def health():
    """Health check endpoint"""
    return {"status": "ok"}
