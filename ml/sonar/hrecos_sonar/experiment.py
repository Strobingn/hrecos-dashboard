"""One synthetic experiment. The numbers are only meaningful inside this generator."""

from __future__ import annotations

from datetime import datetime, timezone

from sonar_node.classify.rules import RulesClassifier
from sonar_node.simulate import generate_tracks

from hrecos_sonar.softmax import fit_softmax

SPLIT = datetime(2026, 6, 1, tzinfo=timezone.utc)
WINDOW_START = datetime(2026, 3, 1, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 8, 1, tzinfo=timezone.utc)
SEED = 20260311
RATE = 0.35
FIT_STEPS = 400
FIT_SEED = 0


def run_experiment() -> dict:
    tracks = generate_tracks(
        WINDOW_START,
        WINDOW_END,
        node_id="westpoint-cornwall",
        seed=SEED,
        rate=RATE,
    )
    train = [track for track in tracks if track.start < SPLIT]
    test = [track for track in tracks if track.start >= SPLIT]
    model = fit_softmax(train, steps=FIT_STEPS, seed=FIT_SEED)
    softmax_pred = model.predict(test)
    rules = RulesClassifier()
    rules_pred = [rules.classify(track).species_id for track in test]
    truth = [track.truth_species for track in test]
    from hrecos_sonar.metrics import score

    return {
        "data": "synthetic",
        "not_field_performance": True,
        "generator": "sonar_node.simulate.generate_tracks",
        "node_id": "westpoint-cornwall",
        "window_start": WINDOW_START.isoformat(),
        "window_end": WINDOW_END.isoformat(),
        "split": "start < 2026-06-01 train, otherwise test",
        "seed": SEED,
        "rate": RATE,
        "n_generated": len(tracks),
        "n_train": len(train),
        "n_test": len(test),
        "softmax": {
            "model_name": "synthetic_softmax",
            "model_version": "0.1.0",
            "steps": FIT_STEPS,
            "fit_seed": FIT_SEED,
            "abstain_below": 0.45,
            "class_weight": "balanced",
            **score(truth, softmax_pred),
        },
        "length_behavior_rules": {
            "model_name": rules.model_name,
            "model_version": rules.model_version,
            **score(truth, rules_pred),
        },
        "model": model,
    }
