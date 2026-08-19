"""Shared Flask extension instances, created here (not in app.py) so
models.py can import `db` without circular imports."""
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
jwt = JWTManager()
