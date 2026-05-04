"""
models/user.py — User model with role-based access and hashed passwords.
"""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models import db


class User(UserMixin, db.Model):
    """
    Represents a system user.
    Roles:
        'admin' — full access to management features
        'user'  — customer / staff who places orders
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")  # 'admin' or 'user'

    # Relationships
    orders = db.relationship("Order", back_populates="user", lazy="dynamic")

    # ── Password helpers ──────────────────────────────────────────────────────
    def set_password(self, password: str) -> None:
        """Hash and store the given plain-text password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True if the given plain-text password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    # ── Convenience ──────────────────────────────────────────────────────────
    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def __repr__(self) -> str:
        return f"<User {self.username!r} ({self.role})>"
