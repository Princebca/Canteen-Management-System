"""
models/__init__.py
Shared SQLAlchemy instance used across all model modules.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
