#!/usr/bin/env python3
"""Generate the deterministic synthetic train and test splits."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hrecos_ml.dataset import write_manifest  # noqa: E402
from hrecos_ml.synthesize import write_split  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-train", type=int, default=48)
    parser.add_argument("--n-test", type=int, default=24)
    parser.add_argument("--train-seed", type=int, default=20260311)
    parser.add_argument("--test-seed", type=int, default=20260917)
    args = parser.parse_args()
    root = ROOT / "data" / "synthetic"
    rows = write_split(root, "train", args.n_train, seed=args.train_seed)
    rows += write_split(root, "test", args.n_test, seed=args.test_seed)
    manifest = ROOT / "data" / "synthetic_manifest.jsonl"
    write_manifest(manifest, rows)
    print(f"wrote {len(rows)} clips to {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
