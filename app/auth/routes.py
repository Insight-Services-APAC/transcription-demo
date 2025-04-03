from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth_bp
from app.auth.forms import LoginForm, RegistrationForm, ChangePasswordForm
from app.models.user import User
from app.extensions import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_temporary_password:
            return redirect(url_for("auth.change_password"))
        if not current_user.is_approved and not current_user.is_admin:
            return redirect(url_for("auth.pending_approval"))
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(
            (User.email == form.username.data) | (User.username == form.username.data)
        ).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash(
                    "Your account is deactivated. Please contact an administrator.",
                    "danger",
                )
                return render_template("auth/login.html", form=form)

            # Check if user is approved (admins are always approved)
            if not user.is_approved and not user.is_admin:
                login_user(user, remember=form.remember.data)
                user.last_login = datetime.utcnow()
                db.session.commit()
                logger.info(f"User {user.username} logged in (pending approval)")
                return redirect(url_for("auth.pending_approval"))

            login_user(user, remember=form.remember.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            logger.info(f"User {user.username} logged in successfully")

            # Redirect to change password page if temporary password
            if user.is_temporary_password:
                flash(
                    "You must change your temporary password before continuing.",
                    "warning",
                )
                return redirect(url_for("auth.change_password"))

            flash("Login successful!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.index"))
        else:
            logger.warning(f"Failed login attempt for {form.username.data}")
            flash("Invalid username or password", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    username = current_user.username
    logout_user()
    logger.info(f"User {username} logged out")
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("Username already taken.", "danger")
            return render_template("auth/register.html", form=form)
        if User.query.filter_by(email=form.email.data).first():
            flash("Email already registered.", "danger")
            return render_template("auth/register.html", form=form)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            is_approved=False,
        )
        user.is_temporary_password = False  # User-defined password
        db.session.add(user)
        db.session.commit()
        logger.info(f"New user registered: {user.username} (awaiting admin approval)")
        flash(
            "Registration successful! Your account is pending admin approval. You will be notified when your account is approved.",
            "warning",
        )
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/profile")
@login_required
def profile():
    # Redirect to change password if temporary password
    if current_user.is_temporary_password:
        flash("You must change your temporary password before continuing.", "warning")
        return redirect(url_for("auth.change_password"))

    # Redirect to pending approval page if not approved
    if not current_user.is_approved and not current_user.is_admin:
        return redirect(url_for("auth.pending_approval"))

    return render_template("auth/profile.html")


@auth_bp.route("/pending-approval")
@login_required
def pending_approval():
    """Page displayed to users whose accounts are pending admin approval"""
    # If user is already approved or is admin, redirect to main page
    if current_user.is_approved or current_user.is_admin:
        return redirect(url_for("main.index"))

    return render_template("auth/pending_approval.html")


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
            return render_template("auth/change_password.html", form=form)

        # Set new password
        current_user.set_password(form.new_password.data)
        current_user.is_temporary_password = False
        db.session.commit()

        logger.info(f"User {current_user.username} changed their password")
        flash("Your password has been updated successfully.", "success")

        return redirect(url_for("main.index"))

    return render_template("auth/change_password.html", form=form)
