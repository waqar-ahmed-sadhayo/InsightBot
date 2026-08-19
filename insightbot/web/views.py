"""Renders the frontend page shells. No server-side data fetching here --
each template's JS (static/js/app.js) calls the JSON API with the JWT
stored in localStorage after login. Keeping views this thin means the
same API is exercised identically by the browser UI, curl, and tests.
"""
from flask import Blueprint, render_template

bp = Blueprint("web", __name__)


@bp.get("/")
def index():
    return render_template("articles.html")


@bp.get("/login")
def login_page():
    return render_template("login.html")


@bp.get("/register")
def register_page():
    return render_template("register.html")


@bp.get("/articles/<article_id>")
def article_detail_page(article_id: str):
    return render_template("article_detail.html", article_id=article_id)


@bp.get("/admin")
def admin_page():
    return render_template("admin.html")
