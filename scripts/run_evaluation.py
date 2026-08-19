#!/usr/bin/env python
"""CLI entry point for the training-vs-held-out accuracy report.

Usage:
    python scripts/run_evaluation.py
    python scripts/run_evaluation.py --group held_out
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from insightbot import settings  # noqa: E402
from insightbot.evaluation.evaluate import main  # noqa: E402

if __name__ == "__main__":
    settings.ensure_utf8_console()
    main()
