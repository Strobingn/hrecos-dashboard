from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from sonar_node.classify.frames import require_frame_stack
from sonar_node.classify.rules import RulesClassifier
from sonar_node.simulate import SimulatedTrack


def _track(**overrides) -> SimulatedTrack:
    start = datetime(2026, 5, 15, 12, tzinfo=timezone.utc)
    base = dict(
        id="00000000-0000-4000-8000-000000000001",
        node_id="westpoint-cornwall",
        start=start,
        end=start + timedelta(seconds=8),
        direction="milling",
        length_cm=70.0,
        depth_m=0.4,
        range_m=8.0,
        speed_mps=0.2,
        behavior="surface_cluster",
        cluster_size=8,
        near_surface=True,
        cluster_id="cluster-1",
        truth_species="atlantic_sturgeon",
        truth_length_cm=200.0,
    )
    base.update(overrides)
    return SimulatedTrack(**base)


def test_rules_use_measurements_and_ignore_the_hidden_truth():
    rules = RulesClassifier()
    # Truth says sturgeon. The track is a surface cluster of bass-sized fish.
    result = rules.classify(_track())
    assert result.species_id == "striped_bass"
    assert result.model_name == "length_behavior_rules"
    assert 0.0 < result.confidence <= 1.0


def test_length_and_behavior_cuts():
    rules = RulesClassifier()
    sturgeon = rules.classify(
        _track(
            length_cm=210,
            depth_m=8,
            behavior="solitary",
            cluster_size=1,
            near_surface=False,
            direction="upstream",
            cluster_id=None,
        )
    )
    assert sturgeon.species_id == "atlantic_sturgeon"
    assert sturgeon.confidence > 0.7

    overlap = rules.classify(
        _track(
            length_cm=115,
            depth_m=6,
            behavior="solitary",
            cluster_size=1,
            near_surface=False,
            direction="upstream",
            cluster_id=None,
        )
    )
    assert overlap.species_id == "atlantic_sturgeon"
    assert overlap.confidence < sturgeon.confidence

    shad = rules.classify(
        _track(
            length_cm=54,
            depth_m=3.2,
            behavior="school",
            cluster_size=10,
            near_surface=False,
            direction="upstream",
        )
    )
    assert shad.species_id == "american_shad"

    herring = rules.classify(
        _track(
            length_cm=27,
            depth_m=3.0,
            behavior="school",
            cluster_size=12,
            near_surface=False,
            direction="upstream",
        )
    )
    assert herring.species_id == "river_herring"


def test_rules_do_not_classify_frames():
    with pytest.raises(NotImplementedError):
        RulesClassifier().classify_frames(np.zeros((4, 8, 8), dtype=np.float32))


def test_frame_stack_shape():
    require_frame_stack(np.zeros((2, 8, 16), dtype=np.float32))
    with pytest.raises(ValueError):
        require_frame_stack(np.zeros((8, 16), dtype=np.float32))
    with pytest.raises(ValueError):
        require_frame_stack(np.zeros((2, 8, 16), dtype=np.uint8))
