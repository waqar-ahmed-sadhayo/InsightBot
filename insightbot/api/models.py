"""User account model for the Flask app (register/login with admin
approval). Deliberately separate from insightbot.storage.models, which
holds *article* data and may live in a different database entirely.
"""
from __future__ import annotations

from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from insightbot.api.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, raw_password: str):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "is_approved": self.is_approved,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Bookmark(db.Model):
    """A user's saved article. Stores only the article_id -- the article
    itself lives in the (separate) article storage backend, so this table
    stays valid regardless of INSIGHTBOT_DB_BACKEND.
    """
    __tablename__ = "bookmarks"
    __table_args__ = (db.UniqueConstraint("user_id", "article_id", name="uq_bookmark_user_article"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    article_id = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
