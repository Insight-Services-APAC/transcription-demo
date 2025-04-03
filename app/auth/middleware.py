from flask import redirect, url_for, request, flash
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)


class UserAccessMiddleware:
    """
    Middleware that handles:
    1. Redirecting users with temporary passwords to the change password page
    2. Restricting access for unapproved users
    """

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.before_request(self.before_request)

    def before_request(self):
        if not current_user.is_authenticated:
            return
        if request.path.startswith("/static/"):
            return
        exempt_routes = [
            "/auth/logout",
            "/auth/change-password",
            "/auth/pending-approval",
            "/auth/profile",
            "/static/",
            "/health",
        ]
        if any((request.path.startswith(route) for route in exempt_routes)):
            return
        if current_user.is_admin:
            return
        if not current_user.is_approved:
            logger.info(
                f"User {current_user.username} blocked from accessing {request.path} - waiting for approval"
            )
            return redirect(url_for("auth.pending_approval"))
        if current_user.is_temporary_password:
            logger.info(
                f"User {current_user.username} redirected to change password page"
            )
            flash(
                "You must change your temporary password before continuing.", "warning"
            )
            return redirect(url_for("auth.change_password"))


def init_password_middleware(app):
    """Initialize the user access middleware for the application."""
    middleware = UserAccessMiddleware(app)
    return middleware
