"""Fit the synthetic softmax and write metrics next to the weights.

The metrics file is a record of this run. Do not edit it by hand.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
_EDGE = Path(__file__).resolve().parents[3] / "edge" / "sonar" / "src"
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_EDGE))

from hrecos_sonar.experiment import run_experiment

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"


def main() -> None:
    result = run_experiment()
    model = result.pop("model")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    np.savez(
        ARTIFACTS / "softmax_weights.npz",
        weights=model.weights,
        mean=model.mean,
        scale=model.scale,
        classes=np.array(model.classes),
    )
    payload = json.loads(json.dumps(result))
    (ARTIFACTS / "synthetic_metrics.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    softmax = payload["softmax"]
    rules = payload["length_behavior_rules"]
    print(
        f"synthetic test n={softmax['n']} "
        f"softmax_accuracy={softmax['accuracy']:.4f} "
        f"rules_accuracy={rules['accuracy']:.4f}"
    )


if __name__ == "__main__":
    main()
