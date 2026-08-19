"""Daily re-run of the ingestion pipeline via APScheduler (BlockingScheduler).

Run as a standalone long-lived process:
    python -m insightbot.scheduler.scheduler

Or, if you'd rather use OS cron instead of an always-on Python process,
skip this module entirely and point cron at scripts/run_pipeline.py:
    0 3 * * *  cd /path/to/InsightBot && venv/bin/python scripts/run_pipeline.py --group all
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from insightbot import settings
from insightbot.pipeline import run_pipeline

logger = logging.getLogger("insightbot.scheduler")


def daily_job():
    logger.info("Starting scheduled daily ingestion run")
    results = run_pipeline(group="all", persist=True)
    ok = sum(1 for r in results if not r["error"])
    logger.info("Scheduled run complete: %d/%d sites succeeded", ok, len(results))


def build_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        daily_job,
        trigger=CronTrigger(hour=settings.DAILY_RUN_HOUR, minute=settings.DAILY_RUN_MINUTE),
        id="insightbot_daily_ingestion",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    return scheduler


if __name__ == "__main__":
    settings.ensure_utf8_console()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sched = build_scheduler()
    logger.info("InsightBot scheduler started. Daily run at %02d:%02d UTC.",
                settings.DAILY_RUN_HOUR, settings.DAILY_RUN_MINUTE)
    sched.start()
