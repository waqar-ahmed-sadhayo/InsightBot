"""Flat-file persistence: every extracted article is appended to a single
JSON array file and a single CSV file under data/processed/. These files
are the source of truth when DB_BACKEND=none, and are always written
regardless of backend so there's a portable, dependency-free record of
every run.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Iterable

from insightbot import settings

FIELDNAMES = [
    "id", "title", "body", "date", "language", "source_url", "domain",
    "image", "fetched_at", "title_method", "body_method", "date_method", "image_method",
]

JSON_PATH = settings.PROCESSED_DIR / "articles.json"
CSV_PATH = settings.PROCESSED_DIR / "articles.csv"


def article_id(source_url: str) -> str:
    return hashlib.sha1(source_url.encode("utf-8")).hexdigest()[:16]


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []


def upsert_articles(records: Iterable[dict], json_path: Path = None, csv_path: Path = None) -> list[dict]:
    """Merges `records` (each must include "source_url") into the JSON/CSV
    store, keyed by article_id(source_url), overwriting any prior version
    of the same article. Returns the full, updated list of records.
    """
    json_path = json_path or JSON_PATH
    csv_path = csv_path or CSV_PATH
    json_path.parent.mkdir(parents=True, exist_ok=True)

    existing = {r["id"]: r for r in _load_json(json_path) if "id" in r}

    for rec in records:
        rid = rec.get("id") or article_id(rec["source_url"])
        rec = {**rec, "id": rid}
        existing[rid] = rec

    all_records = list(existing.values())
    json_path.write_text(json.dumps(all_records, ensure_ascii=False, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for rec in all_records:
            writer.writerow({k: rec.get(k, "") for k in FIELDNAMES})

    return all_records


def load_all(json_path: Path = None) -> list[dict]:
    return _load_json(json_path or JSON_PATH)
