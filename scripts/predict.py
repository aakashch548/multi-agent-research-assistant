#!/usr/bin/env python
"""Classify a job posting from --text or stdin."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fake_job_detector.predict import JobPostingClassifier  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Predict fake vs real job posting")
    parser.add_argument("--text", type=str, default="", help="Job description text")
    parser.add_argument(
        "--model",
        choices=("naive_bayes", "decision_tree"),
        default="naive_bayes",
    )
    parser.add_argument("--models-dir", type=Path, default=ROOT / "models")
    args = parser.parse_args()

    text = args.text.strip()
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    if not text:
        print("Provide --text or pipe input on stdin.", file=sys.stderr)
        return 1

    clf = JobPostingClassifier(models_dir=args.models_dir, model_name=args.model)
    result = clf.predict(text)
    print(result["display"])
    if result["confidence"] is not None:
        print(f"Confidence (predicted class): {result['confidence']:.2%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
