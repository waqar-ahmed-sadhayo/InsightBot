"""Storage layer: persists extracted articles to JSON + CSV (always) and
optionally to MongoDB or MySQL, and exposes a uniform read API
(`get_repository()`) for the Flask backend regardless of which database
backend is configured.
"""
