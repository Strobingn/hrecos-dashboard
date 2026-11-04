#!/usr/bin/env python3
"""Train linear probes on cached embeddings and write the versioned artifact.

The committed artifact is fit on the synthetic training split only. Real
recordings stay out of these weights so the file can be redistributed with
the MIT repository. FishSounds audio is CC BY-NC 4.0.
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hrecos_ml.export_onnx import export_probe_onnx  # noqa: E402
from hrecos_ml.labels import MODEL_NAME, MODEL_VERSION, TRAIN_LABELS  # noqa: E402
from hrecos_ml.metrics import classification_report  # noqa: E402
from hrecos_ml.probe import fit_probe  # noqa: E402

EMBEDDERS = {
    "perch_v2_backbone": ("perch_v2_backbone",),
    "lowband_v1": ("lowband_v1",),
    "perch_v2_backbone+lowband_v1": ("perch_v2_backbone", "lowband_v1"),
}
# Perch alone is the deployed head. The low-band descriptor scores perfectly on the
# synthetic test and, on this run, pulled real sturgeon clips toward drum_knock.
# It is still trained and saved so that comparison can be repeated.
DEFAULT_EMBEDDER = "perch_v2_backbone"


def _matrix(cache: dict, names: tuple[str, ...]) -> np.ndarray:
    parts = [cache[name] for name in names]
    return np.concatenate(parts, axis=1) if len(parts) > 1 else parts[0]


def _versions() -> dict:
    import importlib.metadata as md

    out = {"python": platform.python_version()}
    for dist in ("numpy", "scikit-learn", "onnxruntime", "onnx", "scipy"):
        try:
            out[dist] = md.version(dist)
        except md.PackageNotFoundError:
            out[dist] = None
    return out


def train(cache_path: Path, out_dir: Path) -> dict:
    with np.load(cache_path, allow_pickle=False) as data:
        cache = {key: data[key] for key in data.files}
    labels = np.asarray([str(x) for x in cache["labels"]])
    splits = np.asarray([str(x) for x in cache["splits"]])
    train_mask = splits == "train"
    test_mask = splits == "test"
    if not np.any(train_mask) or not np.any(test_mask):
        raise SystemExit("cache is missing train or test rows")

    reports = {}
    probes = {}
    for name, columns in EMBEDDERS.items():
        missing = [col for col in columns if col not in cache]
        if missing:
            reports[name] = {"skipped": True, "reason": f"missing columns {missing}"}
            continue
        x = _matrix(cache, columns)
        probe = fit_probe(x[train_mask], labels[train_mask])
        pred = probe.predict(x[test_mask])
        report = classification_report(labels[test_mask], pred, list(TRAIN_LABELS))
        report["n_train"] = int(train_mask.sum())
        report["n_features"] = int(x.shape[1])
        if name.startswith("perch") and "lowband" in name:
            perch_dim = cache["perch_v2_backbone"].shape[1]
            coef = np.abs(probe.coef)
            # Features are standardized, so mean |coef| is comparable across blocks.
            report["mean_abs_coef_perch"] = float(coef[:, :perch_dim].mean())
            report["mean_abs_coef_lowband"] = float(coef[:, perch_dim:].mean())
        reports[name] = report
        probes[name] = probe
        print(f"{name}: macro_f1={report['macro_f1']:.4f} accuracy={report['accuracy']:.4f}")

    if DEFAULT_EMBEDDER not in probes:
        raise SystemExit(f"could not fit the default embedder {DEFAULT_EMBEDDER}")

    out_dir.mkdir(parents=True, exist_ok=True)
    probe = probes[DEFAULT_EMBEDDER]
    probe.save(out_dir / "probe.npz")
    export_probe_onnx(probe, out_dir / "probe.onnx")
    for name, other in probes.items():
        slug = name.replace("+", "_")
        other.save(out_dir / f"probe_{slug}.npz")

    metadata = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "embedder": DEFAULT_EMBEDDER,
        "probe_file": "probe.npz",
        "onnx_file": "probe.onnx",
        "perch_onnx": "ml/data/models/perch_v2_backbone.onnx",
        "perch_source": "https://huggingface.co/biodiversica/Perch-onnx-backbone",
        "perch_upstream": "https://www.kaggle.com/models/google/bird-vocalization-classifier",
        "perch_license": "Apache-2.0",
        "sample_rate_hz": 32000,
        "window_s": 5.0,
        "hop_s": 1.0,
        "threshold": 0.5,
        "train_labels": list(TRAIN_LABELS),
        "classes": probe.classes,
        "n_features": probe.n_features,
        "training_split": "synthetic train only",
        "license_note": (
            "Weights were fit on synthetic audio generated in this repository. "
            "They were not fit on FishSounds (CC BY-NC 4.0) or journal supplementary audio."
        ),
        "package_versions": _versions(),
        "synthetic_test_reports": reports,
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    (out_dir / "metrics_synthetic.json").write_text(json.dumps(reports, indent=2))
    return metadata


def main() -> int:
    cache = ROOT / "artifacts" / "cache" / "synthetic.npz"
    out_dir = ROOT / "artifacts" / MODEL_NAME / MODEL_VERSION
    if not cache.is_file():
        raise SystemExit(f"missing {cache}. Run compute_embeddings.py first.")
    train(cache, out_dir)
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
