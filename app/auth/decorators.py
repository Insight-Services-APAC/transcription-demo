from functools import wraps
from flask import abort, flash, redirect, url_for, request
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)


def admin_required(f):
    """
    Decorator to restrict access to admin users only.

    Must be used after @login_required to ensure the user is authenticated.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            logger.warning(
                f"Non-admin user {current_user.username} attempted to access admin page"
            )
            flash("Access denied. Admin privileges required.", "danger")
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


def approval_required(f):
    """
    Decorator to restrict access to approved users only.

    Can be used with or without @login_required as it checks authentication.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))

        if not current_user.is_admin and not current_user.is_approved:
            logger.warning(
                f"Unapproved user {current_user.username} attempted to access {request.path}"
            )
            return redirect(url_for("auth.pending_approval"))

        return f(*args, **kwargs)

    return decorated_function
