import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from hrecos_sonar.experiment import run_experiment
from hrecos_sonar.features import featurize
from hrecos_sonar.plugin import SyntheticSoftmaxClassifier
from sonar_node.classify.rules import RulesClassifier
from sonar_node.simulate import SimulatedTrack


def test_features_ignore_truth_species():
    start = datetime(2026, 5, 15, tzinfo=timezone.utc)
    common = dict(
        id="00000000-0000-4000-8000-000000000010",
        node_id="westpoint-cornwall",
        start=start,
        end=start + timedelta(seconds=5),
        direction="upstream",
        length_cm=54.0,
        depth_m=3.0,
        range_m=6.0,
        speed_mps=0.6,
        behavior="school",
        cluster_size=9,
        near_surface=False,
        cluster_id="c",
        truth_length_cm=54.0,
    )
    a = featurize(SimulatedTrack(**common, truth_species="american_shad"))
    b = featurize(SimulatedTrack(**common, truth_species="striped_bass"))
    assert np.array_equal(a, b)


def test_committed_metrics_match_a_fresh_synthetic_run():
    path = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "artifacts"
        / "synthetic_metrics.json"
    )
    saved = json.loads(path.read_text(encoding="utf-8"))
    fresh = run_experiment()
    fresh.pop("model")
    assert saved["data"] == "synthetic"
    assert saved["not_field_performance"] is True
    assert saved["softmax"]["accuracy"] == pytest.approx(fresh["softmax"]["accuracy"])
    assert saved["length_behavior_rules"]["accuracy"] == pytest.approx(
        fresh["length_behavior_rules"]["accuracy"]
    )
    assert saved["n_test"] == fresh["n_test"]
    assert saved["softmax"]["n"] == saved["n_test"]


def test_plugin_loads_synthetic_weights_and_refuses_frames():
    classifier = SyntheticSoftmaxClassifier()
    assert classifier.model_name == "synthetic_softmax"
    start = datetime(2026, 6, 2, tzinfo=timezone.utc)
    track = SimulatedTrack(
        id="00000000-0000-4000-8000-000000000011",
        node_id="westpoint-cornwall",
        start=start,
        end=start + timedelta(seconds=6),
        direction="milling",
        length_cm=78.0,
        depth_m=0.5,
        range_m=7.0,
        speed_mps=0.15,
        behavior="surface_cluster",
        cluster_size=7,
        near_surface=True,
        cluster_id="spawn",
        truth_species="striped_bass",
        truth_length_cm=80.0,
    )
    result = classifier.classify(track)
    assert result.species_id in {
        "striped_bass",
        "american_shad",
        "river_herring",
        "atlantic_sturgeon",
        None,
    }
    with pytest.raises(NotImplementedError):
        classifier.classify_frames(np.zeros((3, 8, 8), dtype=np.float32))
    # The rules baseline still has to be the thing that names a surface cluster.
    assert RulesClassifier().classify(track).species_id == "striped_bass"
