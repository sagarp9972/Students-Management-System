from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User
from forms import LoginForm, ForgotPasswordForm
from . import auth_bp


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.post_login_redirect"))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.identifier.data.strip()
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user is None or not user.check_password(form.password.data):
            flash("Invalid username/email or password.", "danger")
            return render_template("auth/login.html", form=form)

        if not user.is_active_account:
            flash("Your account has been deactivated. Contact the admin.", "danger")
            return render_template("auth/login.html", form=form)

        login_user(user, remember=form.remember_me.data)
        flash(f"Welcome back, {user.full_name}!", "success")
        next_page = request.args.get("next")
        return redirect(next_page or url_for("auth.post_login_redirect"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/post-login-redirect")
@login_required
def post_login_redirect():
    if current_user.role == "admin":
        return redirect(url_for("admin.dashboard"))
    if current_user.role == "teacher":
        return redirect(url_for("teacher.dashboard"))
    if current_user.role == "student":
        return redirect(url_for("student.dashboard"))
    if current_user.role == "employee":
        return redirect(url_for("employee.dashboard"))
    # Any other/unexpected role falls back to a safe holding page.
    return redirect(url_for("auth.employee_home"))


@auth_bp.route("/employee-home")
@login_required
def employee_home():
    if current_user.role in ("admin", "teacher", "student"):
        return redirect(url_for("auth.post_login_redirect"))
    return render_template("auth/employee_home.html")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        # Always show the same message to avoid leaking which emails are registered.
        flash("If that email is registered, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        f = request.form
        if not current_user.check_password(f.get("current_password", "")):
            flash("Current password is incorrect.", "danger")
        elif f.get("new_password") != f.get("confirm_password"):
            flash("New passwords do not match.", "danger")
        elif len(f.get("new_password", "")) < 6:
            flash("New password must be at least 6 characters.", "danger")
        else:
            current_user.set_password(f["new_password"])
            db.session.commit()
            flash("Password changed successfully.", "success")
            return redirect(url_for("auth.post_login_redirect"))
    return render_template("auth/change_password.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
