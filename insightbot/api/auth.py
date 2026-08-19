"""Auth endpoints: self-service registration (starts unapproved),
login (rejected until an admin approves), and admin-only approval
management.

    POST /api/auth/register        {email, password}          -> 201, pending approval
    POST /api/auth/login           {email, password}           -> 200 {access_token}
    GET    /api/auth/pending         (admin)                     -> list of unapproved users
    POST   /api/auth/approve/<id>    (admin)                     -> approve a user
    DELETE /api/auth/pending/<id>    (admin)                     -> reject/remove a pending user
    GET    /api/auth/me              (authenticated)              -> current user
"""
from __future__ import annotations

import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (create_access_token, get_jwt_identity,
                                 jwt_required)

from insightbot.api.extensions import db
from insightbot.api.models import User

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _current_user() -> User | None:
    identity = get_jwt_identity()
    if identity is None:
        return None
    return db.session.get(User, int(identity))


def admin_required(fn):
    from functools import wraps

    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = _current_user()
        if not user or not user.is_admin:
            return jsonify({"error": "admin privileges required"}), 403
        return fn(*args, **kwargs)

    return wrapper


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not _EMAIL_RE.match(email):
        return jsonify({"error": "valid email is required"}), 400
    if len(password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "an account with this email already exists"}), 409

    user = User(email=email, is_approved=False, is_admin=False)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "registered; awaiting admin approval", "user": user.to_dict()}), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid email or password"}), 401
    if not user.is_approved:
        return jsonify({"error": "account is pending admin approval"}), 403

    token = create_access_token(identity=str(user.id), additional_claims={"is_admin": user.is_admin})
    return jsonify({"access_token": token, "user": user.to_dict()})


@bp.get("/me")
@jwt_required()
def me():
    user = _current_user()
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify(user.to_dict())


@bp.get("/pending")
@admin_required
def pending():
    users = User.query.filter_by(is_approved=False).order_by(User.created_at.asc()).all()
    return jsonify([u.to_dict() for u in users])


@bp.post("/approve/<int:user_id>")
@admin_required
def approve(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    user.is_approved = True
    db.session.commit()
    return jsonify(user.to_dict())


@bp.delete("/pending/<int:user_id>")
@admin_required
def reject(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    if user.is_approved:
        return jsonify({"error": "cannot reject an already-approved account"}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({"id": user_id, "rejected": True})
