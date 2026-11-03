#!/usr/bin/env python3
"""Write probe.onnx for an already trained artifact. ``train.py`` also does this."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hrecos_ml.export_onnx import export_probe_onnx  # noqa: E402
from hrecos_ml.labels import MODEL_NAME, MODEL_VERSION  # noqa: E402
from hrecos_ml.probe import LinearProbe  # noqa: E402


def main() -> int:
    model_dir = ROOT / "artifacts" / MODEL_NAME / MODEL_VERSION
    probe = LinearProbe.load(model_dir / "probe.npz")
    path = export_probe_onnx(probe, model_dir / "probe.onnx")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
