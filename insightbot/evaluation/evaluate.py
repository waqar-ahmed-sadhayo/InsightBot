"""Scores the rule engine's extraction against manually-labeled ground
truth, separately for the training set (used to tune extraction_rules.yaml)
and the held-out set (never tuned against), so the report shows whether
the generic heuristics actually generalize.

Similarity, not exact string match, is used for title/body: news sites
add/remove whitespace, HTML entities, and trailing " | Site Name" suffixes
that a human transcriber wouldn't bother normalizing identically. A field
is "correct" if similarity >= its threshold.
"""
from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from insightbot import settings
from insightbot.pipeline import load_site_list, process_one

TITLE_MATCH_THRESHOLD = 0.85
BODY_MATCH_THRESHOLD = 0.60
GROUND_TRUTH_DIR = Path(__file__).parent / "ground_truth"


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _similarity(a: str, b: str) -> float:
    a, b = _normalize(a), _normalize(b)
    if not a or not b:
        return 0.0
    # A verbatim-correct ground-truth excerpt that happens to be much
    # shorter than the compared extracted text (e.g. a truncated ~35-char
    # ground-truth body against a full multi-paragraph extraction) still
    # gets unfairly punished by SequenceMatcher.ratio(), which is sensitive
    # to the *length difference* between the two strings, not just content
    # overlap -- a correct short prefix can score well under any reasonable
    # threshold purely because of size mismatch. Treat a literal substring
    # match as a perfect score before falling back to fuzzy similarity.
    if b in a:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def load_ground_truth(group: str) -> dict:
    path = GROUND_TRUTH_DIR / f"{group}_ground_truth.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("_readme", None)
    return data


def evaluate_group(group: str) -> dict:
    ground_truth = load_ground_truth(group)
    sites = [s for s in load_site_list(group) if s["url"] in ground_truth]

    rows = []
    for site in sites:
        gt = ground_truth[site["url"]]
        extracted = process_one(site["url"], site["language"])

        title_sim = _similarity(extracted.get("title") or "", gt.get("title") or "")
        body_sim = _similarity((extracted.get("body") or "")[:len(gt.get("body") or "") + 200], gt.get("body") or "")
        date_correct = bool(gt.get("date")) and extracted.get("date") == gt.get("date")

        rows.append({
            "url": site["url"],
            "language": site["language"],
            "error": extracted.get("error"),
            "title_similarity": round(title_sim, 3),
            "title_correct": title_sim >= TITLE_MATCH_THRESHOLD,
            "body_similarity": round(body_sim, 3),
            "body_correct": body_sim >= BODY_MATCH_THRESHOLD,
            "date_correct": date_correct,
            "elapsed_seconds": extracted.get("elapsed_seconds"),
        })

    n = len(rows) or 1
    summary = {
        "group": group,
        "num_sites_scored": len(rows),
        "num_sites_in_config": len(load_site_list(group)),
        "title_accuracy": round(sum(r["title_correct"] for r in rows) / n, 3),
        "body_accuracy": round(sum(r["body_correct"] for r in rows) / n, 3),
        "date_accuracy": round(sum(r["date_correct"] for r in rows) / n, 3),
        "avg_elapsed_seconds": round(sum(r["elapsed_seconds"] or 0 for r in rows) / n, 3),
        "rows": rows,
    }
    return summary


def print_report(training: dict, held_out: dict):
    def line(label, s):
        print(f"{label:<12} sites_scored={s['num_sites_scored']:<3} "
              f"title_acc={s['title_accuracy']:.0%}  body_acc={s['body_accuracy']:.0%}  "
              f"date_acc={s['date_accuracy']:.0%}  avg_time={s['avg_elapsed_seconds']:.2f}s")

    print("=" * 78)
    print("InsightBot Extraction Evaluation Report")
    print("=" * 78)
    line("Training", training)
    line("Held-out", held_out)
    print("-" * 78)
    if training["num_sites_scored"] == 0 or held_out["num_sites_scored"] == 0:
        print("NOTE: ground_truth JSON files still contain placeholder text.")
        print("      Fill in insightbot/evaluation/ground_truth/*.json with real")
        print("      manually-verified titles/bodies/dates to get a real report.")


def main():
    parser = argparse.ArgumentParser(description="Evaluate InsightBot extraction accuracy")
    parser.add_argument("--group", choices=["training", "held_out", "both"], default="both")
    parser.add_argument("--out", default=str(settings.EXPORTS_DIR / "evaluation_report.json"))
    args = parser.parse_args()

    training = evaluate_group("training") if args.group in ("training", "both") else None
    held_out = evaluate_group("held_out") if args.group in ("held_out", "both") else None

    if training and held_out:
        print_report(training, held_out)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"training": training, "held_out": held_out}, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"\nFull report written to {out_path}")


if __name__ == "__main__":
    main()
