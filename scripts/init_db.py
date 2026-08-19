#!/usr/bin/env python
"""One-off setup script: creates the Flask app's user-auth tables and
bootstraps an admin account from INSIGHTBOT_ADMIN_EMAIL/PASSWORD (.env).
Safe to re-run.

Usage:
    python scripts/init_db.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from insightbot import settings  # noqa: E402
from insightbot.api.app import create_app  # noqa: E402


def main():
    if not (settings.BOOTSTRAP_ADMIN_EMAIL and settings.BOOTSTRAP_ADMIN_PASSWORD):
        print("WARNING: INSIGHTBOT_ADMIN_EMAIL / INSIGHTBOT_ADMIN_PASSWORD not set in .env; "
              "user tables will be created but no admin account will exist. "
              "You won't be able to approve registrations until one does.")
    create_app()  # app factory creates tables + bootstraps admin as a side effect
    print(f"Database ready at {settings.SQLALCHEMY_DATABASE_URI}")


if __name__ == "__main__":
    main()
