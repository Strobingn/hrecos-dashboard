"""Scores on a labeled synthetic split. Abstention counts as a miss."""

from __future__ import annotations

import numpy as np

from sonar_node.contract import SPECIES_IDS


def score(truth: list[str], predicted: list[str | None]) -> dict:
    if len(truth) != len(predicted):
        raise ValueError("truth and predicted length differ")
    labels = list(SPECIES_IDS)
    columns = labels + ["abstain"]
    matrix = np.zeros((len(labels), len(columns)), dtype=int)
    label_index = {name: i for i, name in enumerate(labels)}
    for actual, guess in zip(truth, predicted):
        row = label_index[actual]
        column = label_index[guess] if guess in label_index else len(labels)
        matrix[row, column] += 1
    per_class = []
    f1s = []
    for name in labels:
        i = label_index[name]
        support = int(matrix[i].sum())
        tp = int(matrix[i, i])
        fp = int(matrix[:, i].sum() - tp)
        fn = support - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / support if support else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        f1s.append(f1)
        per_class.append(
            {
                "species_id": name,
                "support": support,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )
    correct = sum(actual == guess for actual, guess in zip(truth, predicted))
    return {
        "n": len(truth),
        "accuracy": correct / len(truth) if truth else 0.0,
        "macro_f1": float(np.mean(f1s)) if f1s else 0.0,
        "confusion_columns": columns,
        "confusion_rows": labels,
        "confusion": matrix.tolist(),
        "per_class": per_class,
    }
