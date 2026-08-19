"""HTTP fetching for single pages via requests.

Kept deliberately dumb: one page in, one FetchResult out, never raises for
network-level failures (times out / 4xx / 5xx / connection errors all
degrade to a FetchResult with html=None and an `error` message), matching
the "degrade gracefully" non-functional requirement.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests

from insightbot import settings


@dataclass
class FetchResult:
    url: str
    language: str
    html: Optional[str]
    status_code: Optional[int]
    fetched_at: str  # ISO-8601 UTC
    elapsed_seconds: float
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.html is not None


def _looks_like_html(text: str) -> bool:
    """Sanity check for responses that come back with a 200 status but a
    garbled/binary body -- observed in practice against CDN-fronted sites
    that occasionally serve a compressed or otherwise mangled payload
    without an honest Content-Encoding header, which requests then decodes
    as mojibake instead of raising. A 200 with an unparseable body would
    otherwise silently look like "successfully fetched, nothing to
    extract" instead of the fetch failure it actually is.
    """
    if not text:
        return False
    sample = text[:2000]
    if "�" in sample and sample.count("�") / len(sample) > 0.02:
        return False
    return "<" in sample


def fetch_url(url: str, language: str, timeout: float = None, max_retries: int = None) -> FetchResult:
    """Fetch a single URL. Never raises; failures are reported on the result."""
    timeout = settings.REQUEST_TIMEOUT_SECONDS if timeout is None else timeout
    max_retries = settings.MAX_RETRIES if max_retries is None else max_retries
    headers = {"User-Agent": settings.USER_AGENT, "Accept-Language": f"{language},en;q=0.7"}

    start = time.monotonic()
    last_error = None
    status_code = None

    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            status_code = resp.status_code
            elapsed = time.monotonic() - start
            resp.raise_for_status()
            # Let requests guess encoding from headers, but fall back to
            # apparent_encoding for pages with missing/incorrect charset
            # declarations (common on older Arabic/Russian sites).
            if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = resp.apparent_encoding
            if not _looks_like_html(resp.text):
                last_error = "response body did not look like valid HTML (possible CDN/encoding glitch)"
                continue
            return FetchResult(
                url=url,
                language=language,
                html=resp.text,
                status_code=status_code,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                elapsed_seconds=elapsed,
            )
        except requests.RequestException as exc:
            last_error = str(exc)
            continue

    elapsed = time.monotonic() - start
    return FetchResult(
        url=url,
        language=language,
        html=None,
        status_code=status_code,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=elapsed,
        error=last_error or "unknown fetch error",
    )


def fetch_many(entries: list[dict]) -> list[FetchResult]:
    """entries: [{"url": ..., "language": ...}, ...] -> list[FetchResult]."""
    return [fetch_url(e["url"], e["language"]) for e in entries]
