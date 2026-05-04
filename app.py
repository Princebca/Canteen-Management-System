"""
app.py — Flask application entry point.

Creates and configures the Flask app, initializes extensions,
registers blueprints, configures Flask-Login, and starts the dev server.
"""
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import Config
from models import db
from models.user import User
from routes import register_blueprints


def create_app(config_class=Config):
    """Application factory — creates and returns a configured Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)

    # CSRF protection for all forms
    csrf = CSRFProtect(app)

    # Flask-Login
    login_manager = LoginManager(app)
    login_manager.login_view      = "auth.login"
    login_manager.login_message   = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id: str):
        """Load user from the database by primary key (called on every request)."""
        return db.session.get(User, int(user_id))

    # ── Blueprints ────────────────────────────────────────────────────────────
    register_blueprints(app)

    # ── Error handlers ────────────────────────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    # ── Create tables (safe to run multiple times) ────────────────────────────
    with app.app_context():
        db.create_all()

    return app


# ── Entry point ───────────────────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
