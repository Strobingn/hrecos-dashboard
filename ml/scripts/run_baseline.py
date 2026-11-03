#!/usr/bin/env python3
"""Reproduce the baseline: download, synthesize, embed, train, evaluate."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def _run(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, check=True, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-train", type=int, default=48)
    parser.add_argument("--n-test", type=int, default=24)
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()
    scripts = ROOT / "scripts"
    if not args.skip_download:
        _run([PY, str(scripts / "download_data.py")])
    _run(
        [
            PY,
            str(scripts / "synthesize_data.py"),
            "--n-train",
            str(args.n_train),
            "--n-test",
            str(args.n_test),
        ]
    )
    _run(
        [
            PY,
            str(scripts / "compute_embeddings.py"),
            "--manifest",
            str(ROOT / "data" / "synthetic_manifest.jsonl"),
            "--out",
            str(ROOT / "artifacts" / "cache" / "synthetic.npz"),
        ]
    )
    external = ROOT / "data" / "external_manifest.jsonl"
    if external.is_file():
        _run(
            [
                PY,
                str(scripts / "compute_embeddings.py"),
                "--manifest",
                str(external),
                "--out",
                str(ROOT / "artifacts" / "cache" / "external.npz"),
            ]
        )
    _run([PY, str(scripts / "train.py")])
    _run([PY, str(scripts / "evaluate.py")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
