"""Date parsing helpers used by rules.py. Kept separate because the
month-name tables for Arabic/Russian are long and don't belong inline in
the scoring logic.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from dateutil import parser as dateutil_parser

_ARABIC_MONTHS = {
    "يناير": 1, "كانون الثاني": 1, "فبراير": 2, "شباط": 2, "مارس": 3, "آذار": 3,
    "أبريل": 4, "نيسان": 4, "مايو": 5, "أيار": 5, "يونيو": 6, "حزيران": 6,
    "يوليو": 7, "تموز": 7, "أغسطس": 8, "آب": 8, "سبتمبر": 9, "أيلول": 9,
    "أكتوبر": 10, "تشرين الأول": 10, "نوفمبر": 11, "تشرين الثاني": 11,
    "ديسمبر": 12, "كانون الأول": 12,
}

_RUSSIAN_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
    "январь": 1, "февраль": 2, "март": 3, "апрель": 4, "май": 5, "июнь": 6,
    "июль": 7, "август": 8, "сентябрь": 9, "октябрь": 10, "ноябрь": 11, "декабрь": 12,
}

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

_ISO_LIKE_RE = re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}([T ]\d{1,2}:\d{2}(:\d{2})?)?\b")
_SLASH_RE = re.compile(r"\b\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b")
_EN_TEXT_RE = re.compile(
    r"\b\d{1,2}\s+(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{4}\b|"
    r"\b(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
    re.IGNORECASE,
)


def _try_iso_or_dateutil(raw: str) -> Optional[datetime]:
    try:
        return dateutil_parser.parse(raw, fuzzy=True)
    except (ValueError, OverflowError, TypeError):
        return None


def _try_arabic(raw: str) -> Optional[datetime]:
    normalized = raw.translate(_ARABIC_DIGITS)
    for name, month in _ARABIC_MONTHS.items():
        if name in normalized:
            m = re.search(r"(\d{1,2}).{0,10}" + re.escape(name) + r".{0,10}(\d{4})", normalized)
            if m:
                day, year = int(m.group(1)), int(m.group(2))
                try:
                    return datetime(year, month, day)
                except ValueError:
                    return None
    return None


def _try_russian(raw: str) -> Optional[datetime]:
    for name, month in _RUSSIAN_MONTHS.items():
        if name in raw:
            m = re.search(r"(\d{1,2})\s*" + re.escape(name) + r"\s*(\d{4})", raw)
            if m:
                day, year = int(m.group(1)), int(m.group(2))
                try:
                    return datetime(year, month, day)
                except ValueError:
                    return None
    return None


def parse_date(raw: Optional[str]) -> Optional[str]:
    """Best-effort parse of a raw date string into an ISO-8601 date
    string (YYYY-MM-DD). Returns None rather than raising when nothing
    recognizable is found.
    """
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None

    for attempt in (_try_iso_or_dateutil, _try_arabic, _try_russian):
        try:
            result = attempt(raw)
        except Exception:
            result = None
        if result:
            return result.date().isoformat()
    return None


def scan_text_for_date(text: str) -> Optional[str]:
    """Regex-scans free text (e.g. article body) for a plausible
    publication date when no structured meta tag was found.
    """
    if not text:
        return None
    for pattern in (_ISO_LIKE_RE, _EN_TEXT_RE, _SLASH_RE):
        m = pattern.search(text)
        if m:
            parsed = parse_date(m.group(0))
            if parsed:
                return parsed
    parsed = _try_arabic(text)
    if parsed:
        return parsed.date().isoformat()
    parsed = _try_russian(text)
    if parsed:
        return parsed.date().isoformat()
    return None
