"""
config.py — Application configuration for Canteen Management System.
All configuration values can be overridden via environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()




class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'menu')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max size

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "canteen-super-secret-2024-change-me")

    # ── Database ──────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "canteen.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Business Logic ────────────────────────────────────────────────────────
    # GST percentage applied to every order (set to 0 to disable)
    GST_PERCENT = float(os.environ.get("GST_PERCENT", 5.0))

    # Items with stock <= LOW_STOCK_THRESHOLD appear in the low-stock alert
    LOW_STOCK_THRESHOLD = int(os.environ.get("LOW_STOCK_THRESHOLD", 10))

    # ── WTF / CSRF ────────────────────────────────────────────────────────────
    WTF_CSRF_ENABLED = True
