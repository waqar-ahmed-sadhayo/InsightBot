"""SQLAlchemy ORM model for the MySQL article-storage backend. Independent
of the Flask app's own SQLAlchemy instance (used only for User auth) so
the storage layer has no dependency on Flask.
"""
from __future__ import annotations

from sqlalchemy import Column, String, Text, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class ArticleRecord(Base):
    __tablename__ = "articles"

    id = Column(String(16), primary_key=True)
    title = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    date = Column(String(32), nullable=True)
    language = Column(String(8), nullable=False, index=True)
    source_url = Column(Text, nullable=False)
    domain = Column(String(255), nullable=True, index=True)
    image = Column(Text, nullable=True)
    fetched_at = Column(String(64), nullable=True)
    title_method = Column(String(64), nullable=True)
    body_method = Column(String(64), nullable=True)
    date_method = Column(String(64), nullable=True)
    image_method = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "date": self.date,
            "language": self.language,
            "source_url": self.source_url,
            "domain": self.domain,
            "image": self.image,
            "fetched_at": self.fetched_at,
            "title_method": self.title_method,
            "body_method": self.body_method,
            "date_method": self.date_method,
            "image_method": self.image_method,
        }


def build_mysql_engine(host: str, port: int, user: str, password: str, db_name: str):
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}?charset=utf8mb4"
    engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return engine


def build_session_factory(engine):
    return sessionmaker(bind=engine)
