#!/usr/bin/env python
"""CLI entry point for a one-off ingestion run.

Usage:
    python scripts/run_pipeline.py --group training
    python scripts/run_pipeline.py --group all --no-persist
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from insightbot import settings  # noqa: E402
from insightbot.pipeline import run_pipeline  # noqa: E402


def main():
    settings.ensure_utf8_console()
    parser = argparse.ArgumentParser(description="Run the InsightBot ingestion pipeline")
    parser.add_argument("--group", choices=["training", "held_out", "all"], default="training")
    parser.add_argument("--no-persist", action="store_true", help="Extract only; skip storage writes")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    results = run_pipeline(group=args.group, persist=not args.no_persist)
    ok = sum(1 for r in results if not r["error"])
    slow = sum(1 for r in results if (r["elapsed_seconds"] or 0) > 5)
    print(f"\n{ok}/{len(results)} sites succeeded. {slow} exceeded the 5s target.")
    for r in results:
        if r["error"]:
            print(f"  FAILED  {r['source_url']} -> {r['error']}")


if __name__ == "__main__":
    main()
