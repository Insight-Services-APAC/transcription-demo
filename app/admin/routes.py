from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.user import User
from app.auth.forms import CreateUserForm
from app.extensions import db
from app.admin.utils import generate_temp_password, send_welcome_email
from app.auth.decorators import admin_required
import logging

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    """Admin dashboard home page"""
    return render_template("admin/dashboard.html")


@admin_bp.route("/users")
@login_required
@admin_required
def user_list():
    """Display list of all users"""
    users = User.query.order_by(User.username).all()
    return render_template("admin/user_list.html", users=users)


@admin_bp.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    """Create a new user with a temporary password"""
    form = CreateUserForm()
    if form.validate_on_submit():
        temp_password = generate_temp_password()
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=temp_password,
            is_admin=form.is_admin.data,
            is_temporary_password=True,
            is_approved=True,
        )
        db.session.add(user)
        db.session.commit()
        try:
            send_welcome_email(user.email, user.username, temp_password)
            logger.info(
                f"Admin {current_user.username} created user {user.username} with temporary password"
            )
            flash(
                f"User created successfully. Temporary password: {temp_password}",
                "success",
            )
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
            flash(
                f"User created but could not send welcome email. Temporary password: {temp_password}",
                "warning",
            )
        return redirect(url_for("admin.user_list"))
    return render_template("admin/create_user.html", form=form)


@admin_bp.route("/users/<user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin.user_list"))
    username = user.username
    db.session.delete(user)
    db.session.commit()
    logger.info(f"Admin {current_user.username} deleted user {username}")
    flash(f"User {username} has been deleted.", "success")
    return redirect(url_for("admin.user_list"))


@admin_bp.route("/users/<user_id>/toggle-admin", methods=["POST"])
@login_required
@admin_required
def toggle_admin(user_id):
    """Toggle admin privileges for a user"""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot modify your own admin privileges.", "danger")
        return redirect(url_for("admin.user_list"))
    user.is_admin = not user.is_admin
    db.session.commit()
    status = "granted" if user.is_admin else "revoked"
    logger.info(
        f"Admin {current_user.username} {status} admin privileges for {user.username}"
    )
    flash(f"Admin privileges {status} for {user.username}.", "success")
    return redirect(url_for("admin.user_list"))


@admin_bp.route("/users/<user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_active(user_id):
    """Toggle active status for a user"""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for("admin.user_list"))
    user.is_active = not user.is_active
    db.session.commit()
    status = "activated" if user.is_active else "deactivated"
    logger.info(f"Admin {current_user.username} {status} user {user.username}")
    flash(f"User {user.username} has been {status}.", "success")
    return redirect(url_for("admin.user_list"))


@admin_bp.route("/users/<user_id>/toggle-approval", methods=["POST"])
@login_required
@admin_required
def toggle_approval(user_id):
    """Toggle approval status for a user"""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot change your own approval status.", "danger")
        return redirect(url_for("admin.user_list"))
    user.is_approved = not user.is_approved
    db.session.commit()
    status = "approved" if user.is_approved else "unapproved"
    logger.info(f"Admin {current_user.username} {status} user {user.username}")
    flash(f"User {user.username} has been {status}.", "success")
    return redirect(url_for("admin.user_list"))


@admin_bp.route("/users/<user_id>/reset-password", methods=["POST"])
@login_required
@admin_required
def reset_password(user_id):
    """Reset a user's password to a new temporary password"""
    user = User.query.get_or_404(user_id)
    temp_password = generate_temp_password()
    user.set_password(temp_password)
    user.is_temporary_password = True
    db.session.commit()
    logger.info(f"Admin {current_user.username} reset password for {user.username}")
    flash(
        f"Password for {user.username} has been reset. New temporary password: {temp_password}",
        "success",
    )
    return redirect(url_for("admin.user_list"))
