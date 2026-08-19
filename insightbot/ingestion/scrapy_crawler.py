"""Optional Scrapy-based fallback crawler.

`fetcher.py` (requests) is the default path for the fixed site list. This
module is only needed when you want to *discover* article links on a
domain (crawl) rather than fetch a known URL list, or when a site blocks
plain `requests` (e.g. requires cookie/redirect handling Scrapy manages
better). Scrapy is an optional dependency: importing this module without
it installed raises a clear ImportError only when actually used, not at
package-import time.

Usage:
    python -m insightbot.ingestion.scrapy_crawler --domain example.com \
        --start-url https://example.com --language en --max-pages 50
"""
from __future__ import annotations

import argparse

from insightbot import settings
from insightbot.ingestion.fetcher import FetchResult
from insightbot.ingestion.raw_store import save_raw


def _build_spider_class(start_url: str, language: str, allowed_domain: str, max_pages: int):
    import scrapy  # noqa: local import - optional dependency
    from datetime import datetime, timezone

    class ArticleDiscoverySpider(scrapy.Spider):
        name = "insightbot_discovery"
        start_urls = [start_url]
        allowed_domains = [allowed_domain]
        custom_settings = {
            "USER_AGENT": settings.USER_AGENT,
            "DOWNLOAD_TIMEOUT": settings.REQUEST_TIMEOUT_SECONDS,
            "CONCURRENT_REQUESTS": 4,
            "ROBOTSTXT_OBEY": True,
        }

        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self._seen = 0

        def parse(self, response):
            if self._seen >= max_pages:
                return
            self._seen += 1
            result = FetchResult(
                url=response.url,
                language=language,
                html=response.text,
                status_code=response.status,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                elapsed_seconds=response.meta.get("download_latency", 0.0),
            )
            save_raw(result)

            if self._seen < max_pages:
                for href in response.css("a::attr(href)").getall():
                    yield response.follow(href, callback=self.parse)

    return ArticleDiscoverySpider


def run_crawl(start_url: str, language: str, allowed_domain: str, max_pages: int = 50) -> None:
    """Blocking call: runs a Scrapy crawl and saves every fetched page via
    raw_store.save_raw, exactly like the requests-based fetcher does.
    """
    try:
        from scrapy.crawler import CrawlerProcess
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "Scrapy is not installed. Run `pip install scrapy` to use the "
            "crawling fallback, or use insightbot.ingestion.fetcher for a "
            "fixed URL list."
        ) from exc

    spider_cls = _build_spider_class(start_url, language, allowed_domain, max_pages)
    process = CrawlerProcess(settings={"LOG_LEVEL": "WARNING"})
    process.crawl(spider_cls)
    process.start()


def _main():
    parser = argparse.ArgumentParser(description="InsightBot Scrapy discovery crawler")
    parser.add_argument("--start-url", required=True)
    parser.add_argument("--domain", required=True, help="allowed_domains value, e.g. example.com")
    parser.add_argument("--language", required=True, choices=["en", "ar", "ru"])
    parser.add_argument("--max-pages", type=int, default=50)
    args = parser.parse_args()
    run_crawl(args.start_url, args.language, args.domain, args.max_pages)


if __name__ == "__main__":
    _main()
