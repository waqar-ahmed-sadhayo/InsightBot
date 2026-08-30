"""Central configuration, loaded from environment variables (.env) with
sensible local-development defaults. Nothing here should raise on import
even if optional dependencies (pymongo, mysqlclient) are missing.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def ensure_utf8_console():
    """Reconfigures stdout/stderr to UTF-8. Without this, printing/logging
    Arabic or Russian article titles on a default Windows console (cp1252)
    raises UnicodeEncodeError and crashes the CLI -- call this once at the
    top of any script/entry point that may print extracted text.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Paths -------------------------------------------------------------
DATA_DIR = Path(os.getenv("INSIGHTBOT_DATA_DIR", BASE_DIR / "data"))
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"
CONFIG_DIR = Path(os.getenv("INSIGHTBOT_CONFIG_DIR", BASE_DIR / "config"))
SITES_CONFIG = CONFIG_DIR / "sites.yaml"
EXTRACTION_RULES_CONFIG = CONFIG_DIR / "extraction_rules.yaml"

for _d in (RAW_DIR, PROCESSED_DIR, EXPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- Networking ----------------------------------------------------------
REQUEST_TIMEOUT_SECONDS = float(os.getenv("INSIGHTBOT_REQUEST_TIMEOUT", "5"))
USER_AGENT = os.getenv(
    "INSIGHTBOT_USER_AGENT",
    "InsightBotCrawler/0.1 (+https://example.com/bot; contact=admin@example.com)",
)
MAX_RETRIES = int(os.getenv("INSIGHTBOT_MAX_RETRIES", "2"))

# --- Database (storage layer) --------------------------------------------
# Backend selector: "mongo", "mysql", or "none" (JSON/CSV only).
DB_BACKEND = os.getenv("INSIGHTBOT_DB_BACKEND", "none").lower()

MONGO_URI = os.getenv("INSIGHTBOT_MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("INSIGHTBOT_MONGO_DB", "insightbot")

MYSQL_HOST = os.getenv("INSIGHTBOT_MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("INSIGHTBOT_MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("INSIGHTBOT_MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("INSIGHTBOT_MYSQL_PASSWORD", "")
MYSQL_DB_NAME = os.getenv("INSIGHTBOT_MYSQL_DB", "insightbot")

# --- Flask / API -----------------------------------------------------------
SECRET_KEY = os.getenv("INSIGHTBOT_SECRET_KEY", "dev-secret-change-me")
JWT_EXPIRES_HOURS = int(os.getenv("INSIGHTBOT_JWT_EXPIRES_HOURS", "12"))
SQLALCHEMY_DATABASE_URI = os.getenv(
    "INSIGHTBOT_SQLALCHEMY_URI", f"sqlite:///{DATA_DIR / 'insightbot_app.db'}"
)

# --- Bootstrap admin (created on first `flask` app start if no admin exists) ---
BOOTSTRAP_ADMIN_EMAIL = os.getenv("INSIGHTBOT_ADMIN_EMAIL", "")
BOOTSTRAP_ADMIN_PASSWORD = os.getenv("INSIGHTBOT_ADMIN_PASSWORD", "")

# --- Demo credentials hint on the login page -------------------------------
# Off by default everywhere. Only flip this on (e.g. temporarily on Vercel)
# when you want an interviewer/reviewer to self-serve login -- the values
# shown are a dedicated low-privilege demo account, never the real admin.
SHOW_DEMO_CREDENTIALS = os.getenv("INSIGHTBOT_SHOW_DEMO_CREDENTIALS", "false").lower() == "true"
DEMO_ACCOUNT_EMAIL = os.getenv("INSIGHTBOT_DEMO_EMAIL", "demo@insightbot.dev")
DEMO_ACCOUNT_PASSWORD = os.getenv("INSIGHTBOT_DEMO_PASSWORD", "")

# --- Scheduler -------------------------------------------------------------
DAILY_RUN_HOUR = int(os.getenv("INSIGHTBOT_DAILY_RUN_HOUR", "3"))
DAILY_RUN_MINUTE = int(os.getenv("INSIGHTBOT_DAILY_RUN_MINUTE", "0"))
