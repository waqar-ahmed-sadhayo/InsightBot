"""Flask application factory. Wires together the auth/articles/dashboard
JSON API blueprints, the server-rendered web frontend blueprint, and
bootstraps a first admin user from INSIGHTBOT_ADMIN_EMAIL/PASSWORD (if set
and no admin exists yet) so there's always a way to approve the first
real user.
"""
from __future__ import annotations

from datetime import timedelta

from flask import Flask
from flask_cors import CORS

from insightbot import settings
from insightbot.api.extensions import db, jwt


def _bootstrap_admin():
    from insightbot.api.models import User

    if User.query.filter_by(is_admin=True).first():
        return
    if not (settings.BOOTSTRAP_ADMIN_EMAIL and settings.BOOTSTRAP_ADMIN_PASSWORD):
        return
    admin = User.query.filter_by(email=settings.BOOTSTRAP_ADMIN_EMAIL).first()
    if admin is None:
        admin = User(email=settings.BOOTSTRAP_ADMIN_EMAIL)
        db.session.add(admin)
    admin.set_password(settings.BOOTSTRAP_ADMIN_PASSWORD)
    admin.is_admin = True
    admin.is_approved = True
    db.session.commit()


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="../web/templates",
        static_folder="../web/static",
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = settings.SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=settings.JWT_EXPIRES_HOURS)
    app.config["SECRET_KEY"] = settings.SECRET_KEY

    db.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from insightbot.api.auth import bp as auth_bp
    from insightbot.api.routes_articles import bp as articles_bp
    from insightbot.api.routes_bookmarks import bp as bookmarks_bp
    from insightbot.api.routes_dashboard import bp as dashboard_bp
    from insightbot.web.views import bp as web_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(articles_bp)
    app.register_blueprint(bookmarks_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(web_bp)

    with app.app_context():
        db.create_all()
        _bootstrap_admin()

    @app.get("/api/health")
    def health():
        return {"status": "ok", "db_backend": settings.DB_BACKEND}

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
