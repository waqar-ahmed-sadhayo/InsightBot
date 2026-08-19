"""Computes aggregate stats over all stored articles and exports them as
flat CSVs under data/exports/, in a shape Tableau Desktop can connect to
directly via "Text File" data source (one row per fact, no nested JSON).

Exports produced:
  - by_domain.csv     domain, article_count
  - by_language.csv   language, article_count
  - by_date.csv       date, article_count           (article publication date)
  - keyword_freq.csv  keyword, language, frequency  (top N tokens per language)

See README.md "Building the Tableau dashboard" for how to wire these up.
"""
from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

from insightbot import settings
from insightbot.storage.db_store import get_repository

_TOKEN_RE = re.compile(r"[^\W\d_]{3,}", re.UNICODE)  # words, len>=3, no pure digits

# Minimal generic stopword set (English only -- keyword frequency is a
# rough dashboard signal, not NLP; see README "out of scope" notes for why
# full multilingual stopword lists / tokenizers were not built).
_STOPWORDS_EN = {
    "the", "and", "for", "are", "but", "not", "you", "with", "this", "that",
    "was", "have", "has", "from", "will", "said", "its", "his", "her", "their",
    "they", "who", "what", "when", "where", "which", "also", "more", "than",
    "into", "after", "before", "over", "about", "such", "been", "were", "would",
}


def _write_csv(path: Path, header: list[str], rows: list[tuple]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def compute_stats(articles: list[dict] = None, top_n_keywords: int = 30) -> dict:
    articles = articles if articles is not None else get_repository().all()

    by_domain = Counter(a.get("domain") or "" for a in articles)
    by_language = Counter(a.get("language") or "" for a in articles)
    by_date = Counter(a.get("date") or "unknown" for a in articles)

    keyword_rows = []
    for lang in sorted(by_language):
        lang_articles = [a for a in articles if a.get("language") == lang]
        counter = Counter()
        for a in lang_articles:
            text = f"{a.get('title') or ''} {a.get('body') or ''}".lower()
            tokens = _TOKEN_RE.findall(text)
            if lang == "en":
                tokens = [t for t in tokens if t not in _STOPWORDS_EN]
            counter.update(tokens)
        for word, freq in counter.most_common(top_n_keywords):
            keyword_rows.append((word, lang, freq))

    return {
        "by_domain": sorted(by_domain.items(), key=lambda x: -x[1]),
        "by_language": sorted(by_language.items(), key=lambda x: -x[1]),
        "by_date": sorted(by_date.items()),
        "keyword_freq": keyword_rows,
        "total_articles": len(articles),
    }


def export_all(out_dir: Path = None) -> dict:
    out_dir = out_dir or settings.EXPORTS_DIR
    stats = compute_stats()

    _write_csv(out_dir / "by_domain.csv", ["domain", "article_count"], stats["by_domain"])
    _write_csv(out_dir / "by_language.csv", ["language", "article_count"], stats["by_language"])
    _write_csv(out_dir / "by_date.csv", ["date", "article_count"], stats["by_date"])
    _write_csv(out_dir / "keyword_freq.csv", ["keyword", "language", "frequency"], stats["keyword_freq"])

    return {"out_dir": str(out_dir), "total_articles": stats["total_articles"],
            "files": ["by_domain.csv", "by_language.csv", "by_date.csv", "keyword_freq.csv"]}


if __name__ == "__main__":
    import json
    print(json.dumps(export_all(), indent=2))
