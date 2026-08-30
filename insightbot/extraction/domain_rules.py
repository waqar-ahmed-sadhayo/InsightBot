"""Loads config/extraction_rules.yaml: optional per-domain CSS-selector
overrides for title/body/date. Missing file or missing domain entry is
not an error -- callers always get a (possibly empty) DomainRule and fall
back to the generic heuristic.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import yaml

from insightbot import settings


@dataclass
class DomainRule:
    title_selector: str | None = None
    body_selector: str | None = None
    date_selector: str | None = None
    date_attr: str | None = None  # attribute to read date from; None = element text
    image_selector: str | None = None  # CSS selector for an <img>; its src is used


def domain_of(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


@lru_cache(maxsize=1)
def _load_all(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def get_rule(url: str, config_path: Path = None) -> DomainRule:
    config_path = config_path or settings.EXTRACTION_RULES_CONFIG
    all_rules = _load_all(str(config_path))
    entry = all_rules.get(domain_of(url), {})
    return DomainRule(
        title_selector=entry.get("title_selector"),
        body_selector=entry.get("body_selector"),
        date_selector=entry.get("date_selector"),
        date_attr=entry.get("date_attr"),
        image_selector=entry.get("image_selector"),
    )


def reload_rules():
    """Clears the cached rules file (useful in tests / after editing config)."""
    _load_all.cache_clear()
