"""Article listing/detail/search endpoints. All require a logged-in,
admin-approved user (JWT). Reads go through storage.db_store.get_repository()
so the same endpoints work unchanged regardless of DB_BACKEND.

    GET /api/articles?language=en&domain=example.com&page=1&per_page=20
    GET /api/articles/<id>
    GET /api/articles/search?q=keyword&language=en&domain=example.com&page=1&per_page=20
    GET /api/articles/domains                              -> distinct domains, for filter UI
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from insightbot.storage.db_store import get_repository

bp = Blueprint("articles", __name__, url_prefix="/api/articles")


def _pagination_args():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
    return page, per_page


@bp.get("")
@jwt_required()
def list_articles():
    page, per_page = _pagination_args()
    language = request.args.get("language") or None
    domain = request.args.get("domain") or None
    result = get_repository().list_articles(language=language, domain=domain, page=page, per_page=per_page)
    return jsonify(result)


@bp.get("/search")
@jwt_required()
def search_articles():
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify({"error": "query param 'q' is required"}), 400
    page, per_page = _pagination_args()
    language = request.args.get("language") or None
    domain = request.args.get("domain") or None
    result = get_repository().search(keyword, language=language, domain=domain, page=page, per_page=per_page)
    return jsonify(result)


@bp.get("/domains")
@jwt_required()
def list_domains():
    domains = sorted({a.get("domain") for a in get_repository().all() if a.get("domain")})
    return jsonify(domains)


@bp.get("/<article_id>")
@jwt_required()
def get_article(article_id: str):
    article = get_repository().get(article_id)
    if not article:
        return jsonify({"error": "article not found"}), 404
    return jsonify(article)
