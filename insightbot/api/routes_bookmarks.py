"""Saved-articles endpoints. Bookmarks reference an article_id only; the
article body itself is fetched from the configured article repository, so
this works the same regardless of INSIGHTBOT_DB_BACKEND.

    GET    /api/bookmarks?page=1&per_page=20   -> saved articles (same shape as /api/articles)
    GET    /api/bookmarks/ids                  -> just the bookmarked article ids (for star state)
    POST   /api/bookmarks        {article_id}  -> save an article
    DELETE /api/bookmarks/<article_id>         -> remove a saved article
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from insightbot.api.extensions import db
from insightbot.api.models import Bookmark
from insightbot.storage.db_store import get_repository

bp = Blueprint("bookmarks", __name__, url_prefix="/api/bookmarks")


def _pagination_args():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
    return page, per_page


@bp.get("")
@jwt_required()
def list_bookmarks():
    user_id = int(get_jwt_identity())
    page, per_page = _pagination_args()

    rows = Bookmark.query.filter_by(user_id=user_id).order_by(Bookmark.created_at.desc()).all()
    repo = get_repository()
    articles = [a for a in (repo.get(r.article_id) for r in rows) if a is not None]

    total = len(articles)
    start = max(page - 1, 0) * per_page
    return jsonify({
        "total": total, "page": page, "per_page": per_page,
        "items": articles[start:start + per_page],
    })


@bp.get("/ids")
@jwt_required()
def bookmark_ids():
    user_id = int(get_jwt_identity())
    rows = Bookmark.query.filter_by(user_id=user_id).all()
    return jsonify([r.article_id for r in rows])


@bp.post("")
@jwt_required()
def add_bookmark():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    article_id = (data.get("article_id") or "").strip()
    if not article_id:
        return jsonify({"error": "article_id is required"}), 400

    if not get_repository().get(article_id):
        return jsonify({"error": "article not found"}), 404

    existing = Bookmark.query.filter_by(user_id=user_id, article_id=article_id).first()
    if not existing:
        db.session.add(Bookmark(user_id=user_id, article_id=article_id))
        db.session.commit()
    return jsonify({"article_id": article_id, "saved": True}), 201


@bp.delete("/<article_id>")
@jwt_required()
def remove_bookmark(article_id: str):
    user_id = int(get_jwt_identity())
    Bookmark.query.filter_by(user_id=user_id, article_id=article_id).delete()
    db.session.commit()
    return jsonify({"article_id": article_id, "saved": False})
