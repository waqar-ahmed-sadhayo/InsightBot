"""Persists raw HTML + fetch metadata to disk, keyed by a stable hash of
the URL so re-fetches of the same page overwrite predictably and every
fetch is traceable back to its source article.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from insightbot import settings
from insightbot.ingestion.fetcher import FetchResult


def _slug_for(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def save_raw(result: FetchResult, raw_dir: Path = None) -> dict:
    """Writes <slug>.html (if fetched) and <slug>.meta.json. Returns the
    metadata dict that was written, including the slug and file paths.
    """
    raw_dir = raw_dir or settings.RAW_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    slug = _slug_for(result.url)

    html_path = raw_dir / f"{slug}.html"
    meta_path = raw_dir / f"{slug}.meta.json"

    if result.html is not None:
        html_path.write_text(result.html, encoding="utf-8")

    meta = {
        "slug": slug,
        "url": result.url,
        "language": result.language,
        "status_code": result.status_code,
        "fetched_at": result.fetched_at,
        "elapsed_seconds": result.elapsed_seconds,
        "error": result.error,
        "html_file": html_path.name if result.html is not None else None,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def load_raw_html(slug: str, raw_dir: Path = None) -> str | None:
    raw_dir = raw_dir or settings.RAW_DIR
    html_path = raw_dir / f"{slug}.html"
    if not html_path.exists():
        return None
    return html_path.read_text(encoding="utf-8")


def iter_raw_meta(raw_dir: Path = None):
    """Yields metadata dicts for every page currently stored on disk."""
    raw_dir = raw_dir or settings.RAW_DIR
    for meta_path in sorted(raw_dir.glob("*.meta.json")):
        yield json.loads(meta_path.read_text(encoding="utf-8"))
