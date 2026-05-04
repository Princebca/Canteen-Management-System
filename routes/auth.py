"""
routes/auth.py — Authentication routes: login and logout.

Uses Flask-Login for session management and Werkzeug for password verification.
CSRF protection is applied via Flask-WTF.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models.user import User
from models import db

auth_bp = Blueprint("auth", __name__)


# ── Login ─────────────────────────────────────────────────────────────────────
@auth_bp.route("/", methods=["GET", "POST"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Display login form and handle credential verification."""
    # Redirect already-authenticated users to their dashboard
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard") if current_user.is_admin else url_for("user.menu"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # ── Input validation ──────────────────────────────────────────────────
        if not username or not password:
            flash("Please enter both username and password.", "warning")
            return render_template("auth/login.html")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.username}! 👋", "success")
            # Honour 'next' parameter for protected-page redirects
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            return redirect(url_for("admin.dashboard") if user.is_admin else url_for("user.menu"))

        flash("Invalid username or password. Please try again.", "danger")

    return render_template("auth/login.html")


# ── Logout ────────────────────────────────────────────────────────────────────
@auth_bp.route("/logout")
@login_required
def logout():
    """Log the current user out and redirect to the login page."""
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))


# ── Register ──────────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Display registration form and handle user creation."""
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard") if current_user.is_admin else url_for("user.menu"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        # ── Input validation ──────────────────────────────────────────────────
        if not all([username, email, password, confirm]):
            flash("All fields are required.", "warning")
            return render_template("auth/register.html")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")

        # Check uniqueness
        if User.query.filter_by(username=username).first():
            flash("Username already exists. Please choose another.", "warning")
            return render_template("auth/register.html")
        
        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please login.", "warning")
            return render_template("auth/register.html")

        # ── Create user ───────────────────────────────────────────────────────
        new_user = User(username=username, email=email, role="user")
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! You can now log in. 👋", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")
