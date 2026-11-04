"""Classification metrics used by the evaluation script."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support


def classification_report(y_true: list[str] | np.ndarray, y_pred: list[str] | np.ndarray, labels: list[str]) -> dict:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    per_class = []
    for i, label in enumerate(labels):
        per_class.append(
            {
                "label": label,
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1[i]),
                "support": int(support[i]),
            }
        )
    present = [row for row in per_class if row["support"] > 0]
    macro_f1 = float(np.mean([row["f1"] for row in present])) if present else 0.0
    return {
        "labels": list(labels),
        "per_class": per_class,
        "macro_f1": macro_f1,
        "accuracy": float(np.mean(np.asarray(y_true) == np.asarray(y_pred))) if len(y_true) else 0.0,
        "confusion_matrix": matrix.astype(int).tolist(),
        "n": int(len(y_true)),
    }
