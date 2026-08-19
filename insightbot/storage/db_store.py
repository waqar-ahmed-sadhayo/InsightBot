"""Database persistence + a uniform read repository used by the Flask API.

`settings.DB_BACKEND` selects "mongo", "mysql", or "none". Regardless of
backend, insightbot.storage.json_csv_store always writes the flat-file
copy first (pipeline.py calls both) -- the DB is an optional extra, never
the only place data lives, so the system keeps working with DB_BACKEND
misconfigured or the database temporarily down.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

from insightbot import settings
from insightbot.extraction.domain_rules import domain_of
from insightbot.storage import json_csv_store


def to_domain_record(extracted: dict) -> dict:
    """Adds derived fields (id, domain, created_at) to an extracted-article
    dict before persistence."""
    rec = dict(extracted)
    rec["id"] = rec.get("id") or json_csv_store.article_id(rec["source_url"])
    rec["domain"] = rec.get("domain") or domain_of(rec["source_url"])
    rec.setdefault("fetched_at", datetime.now(timezone.utc).isoformat())
    return rec


# --------------------------------------------------------------------------
# Writers
# --------------------------------------------------------------------------

def save_to_mongo(records: Iterable[dict]) -> int:
    try:
        from pymongo import MongoClient
    except ImportError:
        raise ImportError("pymongo not installed; run `pip install pymongo` or set DB_BACKEND=none")

    client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    coll = client[settings.MONGO_DB_NAME]["articles"]
    count = 0
    for rec in records:
        coll.update_one({"_id": rec["id"]}, {"$set": {**rec, "_id": rec["id"]}}, upsert=True)
        count += 1
    client.close()
    return count


def save_to_mysql(records: Iterable[dict]) -> int:
    from insightbot.storage.models import ArticleRecord, build_mysql_engine, build_session_factory

    engine = build_mysql_engine(
        settings.MYSQL_HOST, settings.MYSQL_PORT, settings.MYSQL_USER,
        settings.MYSQL_PASSWORD, settings.MYSQL_DB_NAME,
    )
    Session = build_session_factory(engine)
    session = Session()
    count = 0
    try:
        for rec in records:
            existing = session.get(ArticleRecord, rec["id"])
            fields = {k: rec.get(k) for k in (
                "title", "body", "date", "language", "source_url", "domain",
                "fetched_at", "title_method", "body_method", "date_method",
            )}
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
            else:
                session.add(ArticleRecord(id=rec["id"], created_at=datetime.now(timezone.utc), **fields))
            count += 1
        session.commit()
    finally:
        session.close()
    return count


def save_articles(records: list[dict]) -> dict:
    """Writes to JSON/CSV always, plus the configured DB backend. Returns
    a summary dict; DB failures are caught and reported, not raised, so a
    down database never aborts the ingestion pipeline.
    """
    records = [to_domain_record(r) for r in records]
    json_csv_store.upsert_articles(records)

    summary = {"flat_file_count": len(records), "db_backend": settings.DB_BACKEND, "db_count": 0, "db_error": None}
    if settings.DB_BACKEND == "mongo":
        try:
            summary["db_count"] = save_to_mongo(records)
        except Exception as exc:
            summary["db_error"] = str(exc)
    elif settings.DB_BACKEND == "mysql":
        try:
            summary["db_count"] = save_to_mysql(records)
        except Exception as exc:
            summary["db_error"] = str(exc)
    return summary


# --------------------------------------------------------------------------
# Uniform read repository (used by the Flask API layer)
# --------------------------------------------------------------------------

class ArticleRepository:
    def list_articles(self, language: Optional[str] = None, domain: Optional[str] = None,
                       page: int = 1, per_page: int = 20) -> dict:
        raise NotImplementedError

    def search(self, keyword: str, language: Optional[str] = None, domain: Optional[str] = None,
               page: int = 1, per_page: int = 20) -> dict:
        raise NotImplementedError

    def get(self, article_id: str) -> Optional[dict]:
        raise NotImplementedError

    def all(self) -> list[dict]:
        raise NotImplementedError


class FlatFileRepository(ArticleRepository):
    def all(self) -> list[dict]:
        return json_csv_store.load_all()

    def _filtered(self, language=None, domain=None):
        rows = self.all()
        if language:
            rows = [r for r in rows if r.get("language") == language]
        if domain:
            rows = [r for r in rows if r.get("domain") == domain]
        return rows

    def _paginate(self, rows, page, per_page):
        total = len(rows)
        start = max(page - 1, 0) * per_page
        return {"total": total, "page": page, "per_page": per_page, "items": rows[start:start + per_page]}

    def list_articles(self, language=None, domain=None, page=1, per_page=20):
        rows = sorted(self._filtered(language, domain), key=lambda r: r.get("fetched_at", ""), reverse=True)
        return self._paginate(rows, page, per_page)

    def search(self, keyword, language=None, domain=None, page=1, per_page=20):
        kw = (keyword or "").lower()
        rows = self._filtered(language, domain)
        rows = [r for r in rows if kw in (r.get("title") or "").lower() or kw in (r.get("body") or "").lower()]
        return self._paginate(rows, page, per_page)

    def get(self, article_id):
        for r in self.all():
            if r.get("id") == article_id:
                return r
        return None


class MongoRepository(ArticleRepository):
    def __init__(self):
        from pymongo import MongoClient
        self._client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
        self._coll = self._client[settings.MONGO_DB_NAME]["articles"]

    def _doc(self, d):
        d = dict(d)
        d["id"] = d.pop("_id", d.get("id"))
        return d

    def all(self):
        return [self._doc(d) for d in self._coll.find()]

    def list_articles(self, language=None, domain=None, page=1, per_page=20):
        query = {}
        if language:
            query["language"] = language
        if domain:
            query["domain"] = domain
        total = self._coll.count_documents(query)
        cursor = self._coll.find(query).sort("fetched_at", -1).skip(max(page - 1, 0) * per_page).limit(per_page)
        return {"total": total, "page": page, "per_page": per_page, "items": [self._doc(d) for d in cursor]}

    def search(self, keyword, language=None, domain=None, page=1, per_page=20):
        query = {"$or": [{"title": {"$regex": keyword, "$options": "i"}},
                          {"body": {"$regex": keyword, "$options": "i"}}]}
        extra = {}
        if language:
            extra["language"] = language
        if domain:
            extra["domain"] = domain
        if extra:
            query = {"$and": [query, extra]}
        total = self._coll.count_documents(query)
        cursor = self._coll.find(query).skip(max(page - 1, 0) * per_page).limit(per_page)
        return {"total": total, "page": page, "per_page": per_page, "items": [self._doc(d) for d in cursor]}

    def get(self, article_id):
        d = self._coll.find_one({"_id": article_id})
        return self._doc(d) if d else None


class MySQLRepository(ArticleRepository):
    def __init__(self):
        from insightbot.storage.models import build_mysql_engine, build_session_factory
        self._engine = build_mysql_engine(
            settings.MYSQL_HOST, settings.MYSQL_PORT, settings.MYSQL_USER,
            settings.MYSQL_PASSWORD, settings.MYSQL_DB_NAME,
        )
        self._Session = build_session_factory(self._engine)

    def all(self):
        from insightbot.storage.models import ArticleRecord
        with self._Session() as session:
            return [r.to_dict() for r in session.query(ArticleRecord).all()]

    def list_articles(self, language=None, domain=None, page=1, per_page=20):
        from insightbot.storage.models import ArticleRecord
        with self._Session() as session:
            q = session.query(ArticleRecord)
            if language:
                q = q.filter(ArticleRecord.language == language)
            if domain:
                q = q.filter(ArticleRecord.domain == domain)
            total = q.count()
            rows = q.order_by(ArticleRecord.created_at.desc()) \
                     .offset(max(page - 1, 0) * per_page).limit(per_page).all()
            return {"total": total, "page": page, "per_page": per_page, "items": [r.to_dict() for r in rows]}

    def search(self, keyword, language=None, domain=None, page=1, per_page=20):
        from insightbot.storage.models import ArticleRecord
        with self._Session() as session:
            like = f"%{keyword}%"
            q = session.query(ArticleRecord).filter(
                (ArticleRecord.title.like(like)) | (ArticleRecord.body.like(like))
            )
            if language:
                q = q.filter(ArticleRecord.language == language)
            if domain:
                q = q.filter(ArticleRecord.domain == domain)
            total = q.count()
            rows = q.offset(max(page - 1, 0) * per_page).limit(per_page).all()
            return {"total": total, "page": page, "per_page": per_page, "items": [r.to_dict() for r in rows]}

    def get(self, article_id):
        from insightbot.storage.models import ArticleRecord
        with self._Session() as session:
            r = session.get(ArticleRecord, article_id)
            return r.to_dict() if r else None


def get_repository() -> ArticleRepository:
    """Factory: returns the read repository matching DB_BACKEND, falling
    back to the flat-file repository if the configured backend can't be
    reached (e.g. optional driver not installed).
    """
    if settings.DB_BACKEND == "mongo":
        try:
            return MongoRepository()
        except Exception:
            return FlatFileRepository()
    if settings.DB_BACKEND == "mysql":
        try:
            return MySQLRepository()
        except Exception:
            return FlatFileRepository()
    return FlatFileRepository()
