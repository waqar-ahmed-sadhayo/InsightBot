"""Renders the frontend page shells. No server-side data fetching here --
each template's JS (static/js/app.js) calls the JSON API with the JWT
stored in localStorage after login. Keeping views this thin means the
same API is exercised identically by the browser UI, curl, and tests.
"""
from flask import Blueprint, render_template

from insightbot import settings

bp = Blueprint("web", __name__)


@bp.get("/")
def index():
    return render_template("articles.html")


@bp.get("/login")
def login_page():
    show_demo = settings.SHOW_DEMO_CREDENTIALS and bool(settings.DEMO_ACCOUNT_PASSWORD)
    return render_template(
        "login.html",
        show_demo_credentials=show_demo,
        demo_email=settings.DEMO_ACCOUNT_EMAIL,
        demo_password=settings.DEMO_ACCOUNT_PASSWORD,
    )


@bp.get("/register")
def register_page():
    return render_template("register.html")


@bp.get("/articles/<article_id>")
def article_detail_page(article_id: str):
    return render_template("article_detail.html", article_id=article_id)


@bp.get("/admin")
def admin_page():
    return render_template("admin.html")
