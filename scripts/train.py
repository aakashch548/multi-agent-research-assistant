#!/usr/bin/env python
"""Train classifiers and write metrics + joblib artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fake_job_detector.config import TrainConfig  # noqa: E402
from fake_job_detector.train import train_models  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Train fake job detection models")
    parser.add_argument(
        "--data-path",
        type=Path,
        default=ROOT / "data" / "raw" / "fake_job_postings.csv",
        help="Path to labeled job postings CSV",
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=ROOT / "models",
        help="Directory for saved models",
    )
    parser.add_argument("--test-size", type=float, default=0.3)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    if not args.data_path.is_file():
        alt = ROOT / "data" / "raw" / "DataSet.csv"
        if alt.is_file():
            args.data_path = alt
        else:
            print(
                f"Dataset not found: {args.data_path}\n"
                "Download from Kaggle and save as data/raw/fake_job_postings.csv\n"
                "See data/README.md",
                file=sys.stderr,
            )
            return 1

    config = TrainConfig(
        data_path=args.data_path,
        models_dir=args.models_dir,
        test_size=args.test_size,
        random_state=args.random_state,
    )
    metrics = train_models(config)
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
