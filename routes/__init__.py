"""
routes/__init__.py — Blueprint registration helper.
"""
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.user import user_bp


def register_blueprints(app):
    """Register all application blueprints on the Flask app."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(user_bp)
