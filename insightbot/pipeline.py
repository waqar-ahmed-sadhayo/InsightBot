"""Orchestrates the full ingestion -> preprocessing -> extraction ->
storage pipeline for a list of {url, language} site entries. This is the
single entry point used by scripts/run_pipeline.py, the scheduler, and
the evaluation script, so all three exercise identical logic.
"""
from __future__ import annotations

import logging
import time

import yaml

from insightbot import settings
from insightbot.extraction.domain_rules import domain_of, get_rule
from insightbot.extraction.rules import extract_article
from insightbot.ingestion.fetcher import fetch_url
from insightbot.ingestion.raw_store import save_raw
from insightbot.preprocessing.cleaner import clean_soup
from insightbot.storage.db_store import save_articles

logger = logging.getLogger("insightbot.pipeline")


def load_site_list(group: str = "training", sites_path=None) -> list[dict]:
    """group: "training", "held_out", or "all"."""
    sites_path = sites_path or settings.SITES_CONFIG
    data = yaml.safe_load(sites_path.read_text(encoding="utf-8")) or {}
    if group == "all":
        return (data.get("training") or []) + (data.get("held_out") or [])
    return data.get(group) or []


def process_one(url: str, language: str) -> dict:
    """Runs one URL through the full pipeline. Never raises: any stage
    failure is captured in the returned dict's `error`/`warnings` fields
    so a single bad site can't abort a batch run.
    """
    start = time.monotonic()
    result = {
        "source_url": url, "language": language, "domain": domain_of(url),
        "title": None, "body": None, "date": None, "error": None, "warnings": [],
        "elapsed_seconds": None,
    }
    try:
        fetch_result = fetch_url(url, language)
        result["fetched_at"] = fetch_result.fetched_at
        save_raw(fetch_result)

        if not fetch_result.ok:
            result["error"] = fetch_result.error or f"HTTP {fetch_result.status_code}"
            return result

        soup = clean_soup(fetch_result.html)
        rule = get_rule(url)
        extracted = extract_article(soup, url, language, rule)

        result.update(
            title=extracted.title,
            body=extracted.body,
            date=extracted.date,
            title_method=extracted.title_method,
            body_method=extracted.body_method,
            date_method=extracted.date_method,
            warnings=extracted.warnings,
        )
    except Exception as exc:  # last-resort guard: never let one site kill a batch
        logger.exception("Unhandled error processing %s", url)
        result["error"] = f"unhandled: {exc}"
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - start, 3)
    return result


def run_pipeline(group: str = "training", persist: bool = True) -> list[dict]:
    """Runs ingestion+extraction for every site in `group` and (by
    default) persists successfully-extracted articles. Returns the full
    list of per-site results (including failures) for reporting.
    """
    entries = load_site_list(group)
    results = []
    for entry in entries:
        r = process_one(entry["url"], entry["language"])
        results.append(r)
        slow = " [SLOW >5s]" if (r["elapsed_seconds"] or 0) > 5 else ""
        logger.info("%s -> title=%r error=%r (%.2fs)%s", entry["url"],
                     (r["title"] or "")[:60], r["error"], r["elapsed_seconds"] or 0, slow)

    if persist:
        ok_records = [r for r in results if not r["error"] and r["title"] is not None]
        if ok_records:
            summary = save_articles(ok_records)
            logger.info("Persisted %d articles (%s)", summary["flat_file_count"], summary)

    return results


if __name__ == "__main__":
    settings.ensure_utf8_console()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_pipeline(group="training")
