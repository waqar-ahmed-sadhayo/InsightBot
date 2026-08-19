"""Vercel entrypoint. Exposes the same Flask app used locally
(insightbot.api.app:app) as the WSGI callable Vercel's Python runtime
expects at module scope.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from insightbot.api.app import app  # noqa: E402
