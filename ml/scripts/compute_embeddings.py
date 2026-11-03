#!/usr/bin/env python3
"""Compute frozen embeddings for a jsonl manifest.

Writes a compressed npz with the waveform window and one matrix per embedder.
Perch weights are read from ``ml/data/models/perch_v2_backbone.onnx``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hrecos_ml.dataset import embed_manifest, read_manifest  # noqa: E402
from hrecos_ml.embeddings import LowBandEmbedder, PerchOnnxEmbedder  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--perch",
        type=Path,
        default=ROOT / "data" / "models" / "perch_v2_backbone.onnx",
    )
    parser.add_argument("--lowband-only", action="store_true")
    args = parser.parse_args()

    rows = read_manifest(args.manifest)
    if not rows:
        raise SystemExit(f"manifest is empty: {args.manifest}")
    embedders = {"lowband_v1": LowBandEmbedder()}
    if not args.lowband_only:
        if not args.perch.is_file():
            raise SystemExit(f"missing Perch ONNX at {args.perch}. Run scripts/download_data.py.")
        embedders["perch_v2_backbone"] = PerchOnnxEmbedder(args.perch)
    print(f"embedding {len(rows)} clips with {list(embedders)}")
    embed_manifest(rows, embedders, cache_path=args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
